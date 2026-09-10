package com.pomp.hskai.widget

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.glance.appwidget.GlanceAppWidgetManager
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.MainActivity
import com.pomp.hskai.core.navigation.AppDestination
import com.pomp.hskai.core.navigation.DeepLinkRouter
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.repository.CourseMapSnapshot
import java.time.ZoneId
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

interface AndroidEventsApi {
    @POST("api/v3/android/events")
    suspend fun record(@Header("Authorization") bearer: String, @Body event: AndroidWidgetEvent): retrofit2.Response<EventResponse>
}

@Serializable
data class EventResponse(val ok: Boolean = false)

/** Projection, refresh and telemetry are independent of the RemoteViews layout. */
class WidgetCoordinator(private val app: HskAiApplication, private val eventsApi: AndroidEventsApi) {
    private val refreshMutex = Mutex()
    private val eventsMutex = Mutex()

    suspend fun publish(snapshot: CourseMapSnapshot, epoch: String) {
        if (snapshot.isStale) { render(); return }
        val map = snapshot.map
        app.widgetStore.save(
            WidgetSnapshot(
                fetchedAtMillis = snapshot.fetchedAtMillis,
                localDay = map.today?.localDay ?: map.progress.localDate.orEmpty(),
                zoneId = ZoneId.systemDefault().id,
                level = map.level,
                lessonOrder = map.currentLesson?.order,
                xp = map.progress.xp,
                streak = map.progress.streak,
                dayComplete = map.today?.complete ?: false,
                foundationRequired = map.foundation?.mustComeFirst == true,
            ),
            epoch,
        )
        render()
    }

    suspend fun refresh() = refreshMutex.withLock {
        val session = app.widgetStore.read()
        if (session.linked) {
            when (val result = app.courseRepository.courseMap()) {
                is ApiResult.Success -> publish(result.value, session.epoch)
                is ApiResult.Failure -> render()
            }
            flushEvents()
        } else render()
    }

    suspend fun render() {
        GlanceAppWidgetManager(app).getGlanceIds(HskAiSmartWidget::class.java).forEach { id ->
            HskAiSmartWidget().update(app, id)
        }
    }

    suspend fun event(name: String, id: String = java.util.UUID.randomUUID().toString()) {
        app.widgetStore.enqueue(AndroidWidgetEvent(name, id))
        flushEvents()
    }

    suspend fun flushEvents() = eventsMutex.withLock {
        val session = app.widgetStore.read()
        if (!session.linked || session.events.isEmpty()) return@withLock
        val token = (app.authRepository.accessToken() as? ApiResult.Success)?.value ?: return@withLock
        for (event in session.events) {
            if (app.widgetStore.read().epoch != session.epoch) break
            when (val result = apiCall { eventsApi.record("Bearer $token", event) }) {
                is ApiResult.Success -> if (result.value.ok) app.widgetStore.acknowledge(session.epoch, event.event_id)
                is ApiResult.Failure -> {
                    if (result.error is com.pomp.hskai.core.network.ApiError.SessionExpired) app.authRepository.invalidateSession()
                    break // Stable IDs are retried on the next open/refresh.
                }
            }
        }
    }
}

object WidgetIntents {
    const val SOURCE = "native_entry_source"
    const val EVENT_ID = "native_entry_event_id"

    fun open(context: Context, source: String, courseOnly: Boolean = false): Intent =
        Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            data = Uri.parse(DeepLinkRouter.uriFor(if (courseOnly) AppDestination.Course else AppDestination.CurrentLesson))
            putExtra(SOURCE, source)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
}
