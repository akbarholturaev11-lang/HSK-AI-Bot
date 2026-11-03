package com.pomp.hskai.widget

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import androidx.compose.ui.graphics.Color
import com.pomp.hskai.R

/** Original panda atlas; frame coordinates exclude neighboring decorative fragments. */
internal object WidgetPandaArt {
    private var sprites: List<Bitmap>? = null
    private var portrait: Bitmap? = null
    private val frames = arrayOf(
        intArrayOf(33,34,193,206),intArrayOf(241,36,394,206),intArrayOf(424,29,601,206),
        intArrayOf(637,84,813,207),intArrayOf(839,32,1023,204),intArrayOf(1043,29,1224,205),
        intArrayOf(20,247,200,414),intArrayOf(235,245,406,412),intArrayOf(433,237,607,414),
        intArrayOf(645,240,808,417),intArrayOf(849,243,1020,415),intArrayOf(1061,239,1226,415),
        intArrayOf(26,450,191,623),intArrayOf(223,447,413,623),intArrayOf(425,496,618,620),
        intArrayOf(633,529,826,610),intArrayOf(851,449,1018,625),intArrayOf(1057,447,1222,622),
        intArrayOf(14,660,209,826),intArrayOf(227,659,400,831),intArrayOf(422,652,621,832),
        intArrayOf(625,689,810,833),intArrayOf(848,671,1015,827),intArrayOf(1040,673,1232,825),
        intArrayOf(21,900,191,1019),intArrayOf(264,920,361,1021),intArrayOf(429,855,606,1030),
        intArrayOf(645,862,803,1025),intArrayOf(844,861,1004,1026),intArrayOf(1048,866,1234,1020),
        intArrayOf(24,1075,198,1233),intArrayOf(232,1066,398,1233),intArrayOf(434,1075,599,1233),
        intArrayOf(646,1068,805,1237),intArrayOf(828,1071,1003,1235),intArrayOf(1046,1072,1230,1233),
    )

    /** The previously approved full-body identity also appears in install help. */
    @Synchronized
    fun portrait(context: Context): Bitmap = portrait ?: run {
        val sheet=BitmapFactory.decodeResource(context.resources,R.drawable.widget_panda_flat_sheet,
            BitmapFactory.Options().apply { inScaled=false })
        val sx=sheet.width/2089f;val sy=sheet.height/753f
        val image=Bitmap.createBitmap(sheet,(21*sx).toInt(),(148*sy).toInt(),
            (633*sx).toInt(),(512*sy).toInt())
        sheet.recycle();portrait=image;image
    }

    /** Pure presentation selection. No account policy, clock learning or sender. */
    fun pose(access: WidgetAccess, visual: WidgetVisual): Int {
        val variant=visual.variant.coerceIn(0,visual.state.variants-1)
        return when {
        access != WidgetAccess.ACTIVE -> 0
        visual.state == WidgetVisualState.COMPLETED -> when {
            visual.special?.kind == WidgetSpecialKind.MILESTONE -> 35
            visual.streakTier == 1 -> 32
            visual.streakTier == 2 -> 33
            visual.streakTier == 3 -> 34
            else -> 30 + variant % 2
        }
        visual.returnBand == 3 -> 27 + variant % 2
        visual.returnBand == 2 -> 26
        visual.returnBand == 1 -> 24 + variant % 2
        visual.personalPhase !in setOf("before_study", "study_time_reached") -> 0
        visual.streakSecured -> 29
        visual.personalPhase == "before_study" -> when(visual.streakTier) {
            1 -> if(variant % 2 == 0) 0 else 3
            2 -> if(variant % 2 == 0) 1 else 4
            3 -> if(variant % 2 == 0) 2 else 5
            else -> 3
        }
        else -> when(visual.state) {
            WidgetVisualState.WAITING -> 6 + (variant + visual.streakTier*4) % 6
            WidgetVisualState.EVENING -> 12 + variant % 4
            WidgetVisualState.LATE -> 16 + variant % 4
            WidgetVisualState.CRITICAL -> 20 + variant % 4
            else -> 0
        }
    }

    }

    @Synchronized
    fun bitmap(context: Context, access: WidgetAccess, visual: WidgetVisual): Bitmap {
        val images = sprites ?: run {
            val sheet = BitmapFactory.decodeResource(context.resources,R.drawable.widget_panda_duo_sheet,
                BitmapFactory.Options().apply { inScaled=false })
            val sx=sheet.width/1254f; val sy=sheet.height/1254f
            val paint=Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
            val result = frames.mapIndexed { index, frame ->
                val source=Rect((frame[0]*sx).toInt(),(frame[1]*sy).toInt(),
                    (frame[2]*sx).toInt(),(frame[3]*sy).toInt())
                // Close-up heads fill the lower card like the reference.
                // Full-body return poses and the tiny lonely pose keep scale.
                val image=Bitmap.createBitmap(256,160,Bitmap.Config.ARGB_8888)
                val rawWidth=frame[2]-frame[0];val rawHeight=frame[3]-frame[1]
                val scale=when(index) {
                    25 -> 1.12f
                    in 24..28 -> minOf(1.45f,158f/rawHeight)
                    else -> minOf(1.45f,246f/rawWidth)
                }
                val width=rawWidth*scale;val height=rawHeight*scale
                val top=maxOf(0f,160-height)
                Canvas(image).drawBitmap(sheet,source,RectF((256-width)/2,top,(256+width)/2,top+height),paint)
                image
            }
            sheet.recycle(); sprites=result; result
        }
        return images[pose(access,visual)]
    }

    data class Palette(val background: Int,val counter: Color,val caption: Color,val outlined: Boolean,
                       val warning: Boolean = false)

    @Suppress("UNUSED_PARAMETER")
    fun palette(dark: Boolean,visual: WidgetVisual): Palette = when {
        visual.streakSecured -> Palette(R.drawable.widget_bg_complete,Color.White,Color(0xFF875100),true)
        visual.returnBand >= 2 -> Palette(when {
            visual.returnBand==2 -> R.drawable.widget_bg_away
            visual.variant%2==1 -> R.drawable.widget_bg_evening
            else -> R.drawable.widget_bg_desert
        },if(visual.variant%2==1) Color.White else Color(0xFFD4D4D4),Color.White,false)
        visual.returnBand == 1 -> Palette(if(visual.variant%2==1) R.drawable.widget_bg_away else R.drawable.widget_bg_sleep,
            Color(0xFFD8DEFF),Color.White,false)
        visual.personalPhase == "before_study" -> Palette(
            if(visual.variant%3==0) R.drawable.widget_bg_early else R.drawable.widget_bg_ready,
            Color.White,Color(0xFFF0FFFC),false)
        visual.personalPhase !in setOf("before_study","study_time_reached") ->
            Palette(R.drawable.widget_bg_early,Color.White,Color(0xFFF0FFFC),false)
        visual.state == WidgetVisualState.COMPLETED -> Palette(R.drawable.widget_bg_complete,Color.White,Color(0xFF875100),true)
        else -> when(visual.state) {
            WidgetVisualState.CRITICAL -> Palette(R.drawable.widget_bg_critical,Color(0xFFFFB6B8),Color(0xFFFFDADD),false,visual.streakAtRisk)
            WidgetVisualState.LATE -> Palette(R.drawable.widget_bg_late,Color(0xFFFFCAC9),Color.White,false,visual.streakAtRisk)
            WidgetVisualState.EVENING -> Palette(R.drawable.widget_bg_evening,Color(0xFFFFC5F0),Color.White,false,visual.streakAtRisk)
            WidgetVisualState.WAITING -> Palette(R.drawable.widget_bg_waiting,Color(0xFFE9DEFF),Color.White,false)
            else -> Palette(R.drawable.widget_bg_ready,Color.White,Color(0xFFF0FFFC),false)
        }
    }
}
