package com.pomp.hskai.core.design.components

import android.util.Log
import android.view.View
import android.widget.ImageView
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.res.stringResource
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

/**
 * Draw the bundled HSK 3.0 covers with the platform ImageView rather than a
 * Compose tint/blend shader. Some Android renderers leave the tinted JPEG blank
 * while still reserving its layout area. No network request is involved.
 *
 * The Compose book silhouettes remain visible behind the transparent ImageView
 * if an OEM fails to decode or draw the bundled asset.
 */
@Composable
fun Hsk30BooksHeader(isNew: Boolean, modifier: Modifier = Modifier) {
    val booksDescription = stringResource(R.string.hsk30_promo_books_desc)
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("HSK 3.0", color = PompColors.Ink, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            if (isNew) {
                Surface(color = PompColors.JadeSoft, shape = RoundedCornerShape(5.dp)) {
                    Text(
                        stringResource(R.string.hsk_course_new_section_badge),
                        color = if (PompColors.IsDark) PompColors.Jade else PompColors.DoneDepth,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 0.7.sp,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp),
                    )
                }
            }
        }
        Spacer(Modifier.height(12.dp))
        Box(Modifier.fillMaxWidth().aspectRatio(1.65f)) {
            Hsk30BooksFallback(Modifier.matchParentSize())
            AndroidView(
                factory = { context ->
                    ImageView(context).apply {
                        scaleType = ImageView.ScaleType.CENTER_CROP
                        // Software drawing avoids vendor-specific Compose/GPU blend bugs.
                        setLayerType(View.LAYER_TYPE_SOFTWARE, null)
                        try {
                            setImageResource(R.drawable.hsk30_course_books)
                        } catch (error: RuntimeException) {
                            Log.w("Hsk30BooksHeader", "Bundled HSK book cover unavailable", error)
                            setImageDrawable(null)
                        }
                    }
                },
                update = { it.contentDescription = booksDescription },
                modifier = Modifier.matchParentSize(),
            )
        }
    }
}

/** Visible even if the OEM's image decoder cannot render the packaged JPEG. */
@Composable
private fun Hsk30BooksFallback(modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.padding(horizontal = 12.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(9.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        (1..3).forEach { level ->
            Surface(
                modifier = Modifier.weight(1f).fillMaxHeight(0.8f),
                shape = RoundedCornerShape(9.dp),
                color = PompColors.PaperRaised,
                border = BorderStroke(1.dp, PompColors.Divider),
                shadowElevation = 2.dp,
            ) {
                Column(
                    modifier = Modifier.fillMaxSize().padding(9.dp),
                    verticalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text("汉语", color = PompColors.InkSecondary, fontSize = 13.sp)
                    Column {
                        Text("HSK", color = PompColors.Ink, fontSize = 17.sp, fontWeight = FontWeight.Bold)
                        Text("$level", color = PompColors.Cinnabar, fontSize = 26.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
