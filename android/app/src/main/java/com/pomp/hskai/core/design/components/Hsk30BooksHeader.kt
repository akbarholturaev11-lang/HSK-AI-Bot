package com.pomp.hskai.core.design.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors

/** Reuses the learner's original covers; crops only the photograph's white margins. */
@Composable
fun Hsk30BooksHeader(isNew: Boolean, modifier: Modifier = Modifier) {
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("HSK 3.0", color = PompColors.Ink, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            if (isNew) {
                Surface(color = PompColors.JadeSoft, shape = RoundedCornerShape(5.dp)) {
                    Text(
                        "NEW",
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
        Image(
            painter = painterResource(R.drawable.hsk30_course_books),
            contentDescription = stringResource(R.string.hsk30_promo_books_desc),
            contentScale = ContentScale.Crop,
            colorFilter = ColorFilter.tint(PompColors.Paper, BlendMode.Multiply),
            modifier = Modifier.fillMaxWidth().aspectRatio(1.65f),
        )
    }
}
