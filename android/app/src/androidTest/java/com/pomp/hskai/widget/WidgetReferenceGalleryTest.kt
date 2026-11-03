package com.pomp.hskai.widget

import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.view.View
import android.widget.FrameLayout
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
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Real native rendering fixtures; no account, provider or efficacy acceptance. */
@OptIn(ExperimentalGlanceRemoteViewsApi::class)
@RunWith(AndroidJUnit4::class)
class WidgetReferenceGalleryTest {
    @Test fun allReferencePosesRenderWithRealCaptionsAndTransparentArt() = runBlocking {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        val choices=sortedMapOf<Int,WidgetVisual>()
        val states=listOf(WidgetVisualState.DAY,WidgetVisualState.WAITING,WidgetVisualState.EVENING,
            WidgetVisualState.LATE,WidgetVisualState.CRITICAL,WidgetVisualState.COMPLETED)
        fun keep(v: WidgetVisual) { choices.putIfAbsent(WidgetPandaArt.pose(WidgetAccess.ACTIVE,v),v) }
        for(state in states) for(variant in 0 until state.variants) for(tier in listOf(3,1,2,0)) {
            val phase=when(state) { WidgetVisualState.DAY -> "before_study"
                WidgetVisualState.COMPLETED -> "completed"; else -> "study_time_reached" }
            val v=WidgetVisual(state,variant,personalPhase=phase,completionReason="goal_completed",
                streakTier=tier,streakSecured=state==WidgetVisualState.COMPLETED,
                streakAtRisk=tier>0 && state.urgency>=2)
            keep(v)
            if(state==WidgetVisualState.COMPLETED) keep(v.copy(special=WidgetSpecialState(WidgetSpecialKind.MILESTONE,30)))
            else {
                for(band in 1..3) keep(v.copy(returnBand=band,streakTier=0,streakAtRisk=false))
                keep(v.copy(streakSecured=true,streakAtRisk=false))
            }
        }
        assertEquals((0..35).toSet(),choices.keys)
        val now=ZonedDateTime.now()
        val density=context.resources.displayMetrics.density
        val width=(130*density).toInt();val height=(110*density).toInt()
        val gap=(8*density).toInt()
        val output=File(context.getExternalFilesDir(null),
            InstrumentationRegistry.getArguments().getString("widgetQaOutput") ?: "widget-reference-${System.nanoTime()}")
        assertTrue(output.mkdirs() || output.isDirectory)
        val renderer=GlanceRemoteViews()
        for(language in listOf("uz","ru","tg")) {
            val localized=context.createConfigurationContext(Configuration(context.resources.configuration).apply {
                setLocale(Locale.forLanguageTag(language))
            })
            val sheet=Bitmap.createBitmap((width+gap)*6+gap,(height+gap)*6+gap,Bitmap.Config.ARGB_8888)
            val canvas=Canvas(sheet);canvas.drawColor(Color.rgb(31,46,52))
            for((index,visual) in choices) {
                val art=WidgetPandaArt.bitmap(localized,WidgetAccess.ACTIVE,visual)
                assertEquals(256,art.width);assertEquals(160,art.height)
                assertEquals("Opaque outer corner for pose $index",0,Color.alpha(art.getPixel(0,0)))
                assertEquals(0,Color.alpha(art.getPixel(255,0)))
                assertTrue("Empty pose $index",(0 until art.height).any { y ->
                    (0 until art.width).any { x -> Color.alpha(art.getPixel(x,y))>200 }
                })
                val count=when { visual.returnBand>0 -> 0; visual.special!=null -> 30
                    visual.streakTier==1 -> 2; visual.streakTier==2 -> 12; visual.streakTier==3 -> 123; else -> 0 }
                val session=WidgetSession(linked=true,snapshot=WidgetSnapshot(now.toInstant().toEpochMilli(),
                    now.toLocalDate().toString(),now.zone.id,"hsk1",6,500,count,
                    visual.state==WidgetVisualState.COMPLETED,false))
                val views=renderer.compose(localized,DpSize(130.dp,110.dp)) {
                    WidgetContent(localized,session,WidgetAccess.ACTIVE,false,visual)
                }.remoteViews
                instrumentation.runOnMainSync {
                    val view=views.apply(localized,FrameLayout(localized))
                    view.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),
                        View.MeasureSpec.makeMeasureSpec(height,View.MeasureSpec.EXACTLY))
                    view.layout(0,0,width,height)
                    val bitmap=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888)
                    view.draw(Canvas(bitmap))
                    canvas.drawBitmap(bitmap,(gap+(index%6)*(width+gap)).toFloat(),
                        (gap+(index/6)*(height+gap)).toFloat(),null)
                    File(output,"$language-pose-${index.toString().padStart(2,'0')}.png").outputStream().use {
                        bitmap.compress(Bitmap.CompressFormat.PNG,100,it)
                    }
                    bitmap.recycle()
                }
            }
            File(output,"$language-reference-gallery.png").outputStream().use {
                sheet.compress(Bitmap.CompressFormat.PNG,100,it)
            }
            sheet.recycle()
        }
    }
}
