package com.pomp.hskai.widget

import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.glance.appwidget.ExperimentalGlanceRemoteViewsApi
import androidx.glance.appwidget.GlanceRemoteViews
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.time.ZonedDateTime
import java.util.Locale
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.encodeToJsonElement
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Layout fixtures only; not real-account, provider or launcher acceptance. */
@OptIn(ExperimentalGlanceRemoteViewsApi::class)
@RunWith(AndroidJUnit4::class)
class WidgetPersonalLayoutTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext

    @Test fun personalCopyFitsAllExistingSizesLanguagesAndThemes() = runBlocking {
        val renderer = GlanceRemoteViews()
        val sizes = listOf(DpSize(130.dp,48.dp), DpSize(130.dp,110.dp), DpSize(260.dp,110.dp))
        val states = listOf("neutral" to "personal_time_unknown", "before_study" to "before_personal_time",
            "study_time_reached" to "personal_time_reached", "completed" to "goal_completed",
            "completed" to "plan_completed", "completed" to "course_completed")
        for (language in listOf("uz","ru","tg")) for (dark in listOf(false,true)) for ((phase,reason) in states) {
            val now = ZonedDateTime.now()
            val day = now.toLocalDate().toString()
            val epoch = "00000000-0000-4000-8000-000000000001"
            val binding = "a".repeat(64)
            val complete = phase == "completed"
            val course = reason == "course_completed"
            val time = phase in setOf("before_study","study_time_reached")
            val envelope = WidgetPersonalContext(1,"smart-widget-context-v1",binding,epoch,2,
                now.minusSeconds(1).toInstant().toString(), minOf(now.plusMinutes(30).toInstant(),
                    now.toLocalDate().plusDays(1).atStartOfDay(now.zone).toInstant()).toString(),
                "hsk1","hsk20",day,now.zone.id,if(course)100 else 5,100,
                if(reason=="goal_completed")20 else 0,20,if(reason=="goal_completed")"met" else "not_proven",
                reason=="plan_completed",if(time)"14:00" else null,if(time)"saved" else "unknown",
                "layout_fixture",phase,reason,if(complete)"course" else "continue",if(complete)null else 6,
                emptyList(),null,false,true)
            val raw = Json.encodeToJsonElement(envelope)
            assertNotNull(WidgetPersonalContext.parse(raw))
            val session = WidgetSession(epoch=epoch,linked=true,contextBinding=binding,snapshot=WidgetSnapshot(
                now.toInstant().toEpochMilli(),day,now.zone.id,"hsk1",6,500,8,true,false,
                dailyXp=500,goalXp=20,personalContext=raw))
            val localized = context.createConfigurationContext(Configuration(context.resources.configuration).apply {
                setLocale(Locale.forLanguageTag(language)) })
            for (size in sizes) {
                val access = WidgetStateResolver.resolve(session,now)
                val visual = WidgetVisualResolver.resolve(session,now)
                val views = renderer.compose(localized,size) { WidgetContent(localized,session,access,dark,visual) }.remoteViews
                instrumentation.runOnMainSync {
                    val parent=FrameLayout(localized)
                    val view=views.apply(localized,parent)
                    val density=context.resources.displayMetrics.density
                    val width=(size.width.value*density).toInt();val height=(size.height.value*density).toInt()
                    view.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),
                        View.MeasureSpec.makeMeasureSpec(height,View.MeasureSpec.EXACTLY));view.layout(0,0,width,height)
                    fun labels(node: View): List<TextView> = when(node) {
                        is TextView -> listOf(node)
                        is ViewGroup -> (0 until node.childCount).flatMap { labels(node.getChildAt(it)) }
                        else -> emptyList()
                    }
                    val texts=labels(view)
                    assertTrue(texts.isNotEmpty())
                    val expected=localized.getString(WidgetArt.assetFor(access,visual).text)
                    assertTrue("Missing personal copy: $language $reason $size",texts.any { it.text.toString()==expected })
                    assertFalse("Reward XP used as verified goal",texts.any { it.text.contains("500") })
                    if (size.height.value > 48) texts.filter { it.text.toString()==expected }.forEach { label ->
                        val layout=label.layout
                        if(layout!=null) for(line in 0 until layout.lineCount)
                            assertEquals("Truncated personal copy: $language $reason $size",0,layout.getEllipsisCount(line))
                    }

                    texts.forEach { assertTrue("Clipped: $language $reason $size",it.height >= (it.layout?.height ?: 0)) }
                    val bitmap=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888)
                    view.draw(Canvas(bitmap))
                    val directory=File(context.getExternalFilesDir(null),"widget-personal-qa").apply { mkdirs() }
                    File(directory,"$language-$reason-${if(dark)"dark" else "light"}-${size.width.value.toInt()}x${size.height.value.toInt()}.png")
                        .outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG,100,it) }
                    bitmap.recycle()
                }
            }
        }
    }
}
