package com.pomp.hskai.widget

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.ui.graphics.Color
import com.pomp.hskai.R

/** Generated flat panda poses; original scene assets remain available for rollback. */
internal object WidgetPandaArt {
    private var sprites: List<Bitmap>? = null

    @Synchronized
    fun bitmap(context: Context, access: WidgetAccess, visual: WidgetVisual): Bitmap {
        val images = sprites ?: run {
            val sheet = BitmapFactory.decodeResource(context.resources,R.drawable.widget_panda_flat_sheet,
                BitmapFactory.Options().apply { inSampleSize=2; inScaled=false })
            // Exact approved atlas frames exclude a tiny neighboring-paw fragment.
            val frames=arrayOf(intArrayOf(21,148,654,660),intArrayOf(715,130,1370,657),
                intArrayOf(1389,141,2083,650))
            val sx=sheet.width/2089f; val sy=sheet.height/753f
            val result = (0..2).map { index ->
                val frame=frames[index]
                val x=(frame[0]*sx).toInt();val y=(frame[1]*sy).toInt()
                val frameRight=kotlin.math.ceil(frame[2]*sx).toInt().coerceAtMost(sheet.width)
                val frameBottom=kotlin.math.ceil(frame[3]*sy).toInt().coerceAtMost(sheet.height)
                val tile=Bitmap.createBitmap(sheet,x,y,frameRight-x,frameBottom-y)
                val pixels=IntArray(tile.width*tile.height)
                tile.getPixels(pixels,0,tile.width,0,0,tile.width,tile.height)
                var left=tile.width; var top=tile.height; var right=0; var bottom=0
                for(y in 0 until tile.height) for(x in 0 until tile.width) {
                    if((pixels[y*tile.width+x] ushr 24)>32) {
                        left=minOf(left,x);right=maxOf(right,x);top=minOf(top,y);bottom=maxOf(bottom,y)
                    }
                }
                require(left<=right && top<=bottom) { "Empty panda sprite" }
                val crop=Bitmap.createBitmap(tile,left,top,right-left+1,bottom-top+1)
                val scale=256f/maxOf(crop.width,crop.height)
                val image=Bitmap.createScaledBitmap(crop,maxOf(1,(crop.width*scale).toInt()),
                    maxOf(1,(crop.height*scale).toInt()),true)
                if(image!==crop) crop.recycle()
                if(tile!==crop) tile.recycle()
                image
            }
            sheet.recycle()
            sprites=result
            result
        }
        val pose = when {
            access != WidgetAccess.ACTIVE -> 0
            visual.state == WidgetVisualState.COMPLETED -> 2
            visual.personalPhase == "study_time_reached" -> 1
            else -> 0
        }
        return images[pose]
    }

    data class Palette(val background: Color,val counter: Color,val caption: Color,val outlined: Boolean)

    fun palette(dark: Boolean,visual: WidgetVisual): Palette = when {
        visual.state == WidgetVisualState.COMPLETED -> Palette(Color(0xFFF2FFE9),Color.White,Color(0xFF985000),true)
        visual.personalPhase == "study_time_reached" -> Palette(
            if(dark) Color(0xFF65348C) else Color(0xFF7A429D),Color(0xFFE4B3FF),Color(0xFFF3DEFF),false)
        else -> Palette(if(dark) Color(0xFF59438B) else Color(0xFF7154AB),
            Color(0xFFDCC6FF),Color(0xFFF0E8FF),false)
    }
}
