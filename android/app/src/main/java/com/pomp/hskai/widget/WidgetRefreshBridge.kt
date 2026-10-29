package com.pomp.hskai.widget

import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.repository.CourseMapper
import com.pomp.hskai.domain.model.CourseMap
import java.time.ZonedDateTime
import kotlinx.serialization.json.*

internal fun widgetSnapshot(map: CourseMap, fetchedAt: Long, zoneId: String) = WidgetSnapshot(
    fetchedAtMillis = fetchedAt,
    localDay = map.today?.localDay ?: map.progress.localDate.orEmpty(),
    zoneId = zoneId,
    level = map.level,
    lessonOrder = map.currentLesson?.order,
    xp = map.progress.xp,
    streak = map.progress.streak,
    dayComplete = map.today?.complete ?: false,
    foundationRequired = map.foundation?.mustComeFirst == true,
    dailyXp = map.progress.dailyXp,
    goalXp = map.today?.goalXp ?: 0,
)

/** Live passive reads only: no Room replay, consent, notification or learning event. */
internal class WidgetRefreshBridge(
    private val store: WidgetStore,
    private val session: suspend () -> ApiResult<AuthRepository.AuthenticatedSession>,
    private val commitCurrent: suspend (Long, suspend () -> Unit) -> Boolean,
    private val invalidate: suspend (Long) -> Unit,
    private val fetch: suspend (String, String, Int) -> ApiResult<JsonObject>,
    private val clock: () -> ZonedDateTime = ZonedDateTime::now,
) {
    private val json = Json { ignoreUnknownKeys = true }

    suspend fun refresh() {
        val local = store.read()
        if (!local.linked) return
        val ticket = store.beginRefresh(local.epoch) ?: return
        val started = clock()
        val proof = when (val result = session()) {
            is ApiResult.Success -> result.value
            is ApiResult.Failure -> { store.failedRefresh(ticket); return }
        }
        val response = fetch(proof.token, ticket.epoch, started.offset.totalSeconds / 60)
        if (response is ApiResult.Failure) {
            if (response.error is ApiError.SessionExpired) invalidate(proof.generation)
            else commitCurrent(proof.generation) { store.failedRefresh(ticket) }
            return
        }
        val raw = (response as ApiResult.Success).value
        val dto = runCatching { json.decodeFromJsonElement(CourseMapDto.serializer(), raw) }.getOrNull()
        commitCurrent(proof.generation) {
            val now = clock()
            if (dto == null || !dto.ok || dto.units.isEmpty() || started.zone.id != now.zone.id) {
                store.failedRefresh(ticket)
            } else {
                store.savePersonal(widgetSnapshot(CourseMapper.toDomain(dto), now.toInstant().toEpochMilli(), now.zone.id),
                    raw["widget_context"]?.takeUnless { it == JsonNull }, ticket, now, clock)
            }
        }
    }
}
