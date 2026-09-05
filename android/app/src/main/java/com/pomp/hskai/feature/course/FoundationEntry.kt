package com.pomp.hskai.feature.course

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.domain.model.CourseFoundation

/** Mini App `.foundation-entry`, rendered from the same server-owned foundation state. */
@Composable
internal fun FoundationEntry(
    foundation: CourseFoundation,
    modifier: Modifier = Modifier,
) {
    val done = foundation.completed
    Surface(
        color = PompColors.PaperRaised,
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, Color(0xFFC2403A).copy(alpha = 0.25f)),
        modifier = modifier
            .fillMaxWidth()
            .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 18.dp),
    ) {
        Box(
            modifier = Modifier.background(
                Brush.linearGradient(
                    listOf(
                        Color(0xFFFFF8F1),
                        PompColors.PaperRaised,
                    ),
                ),
            ),
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Surface(
                    color = PompColors.Cinnabar,
                    shape = RoundedCornerShape(15.dp),
                    modifier = Modifier.size(50.dp),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            text = "零",
                            style = PompTextStyles.hanziSmall.copy(
                                fontSize = 25.sp,
                                fontWeight = FontWeight.SemiBold,
                            ),
                            color = PompColors.Paper,
                        )
                    }
                }

                Spacer(Modifier.width(13.dp))

                androidx.compose.foundation.layout.Column(
                    modifier = Modifier.weight(1f),
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = stringResource(R.string.course_foundation_title),
                            style = MaterialTheme.typography.titleSmall.copy(
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                            ),
                            color = PompColors.Ink,
                        )
                        if (done) {
                            Spacer(Modifier.width(5.dp))
                            Icon(
                                Icons.Filled.CheckCircle,
                                contentDescription = null,
                                tint = PompColors.Jade,
                                modifier = Modifier.size(16.dp),
                            )
                        }
                    }
                    Text(
                        text = stringResource(R.string.course_foundation_subtitle),
                        style = MaterialTheme.typography.bodySmall.copy(
                            fontSize = 12.sp,
                            lineHeight = 16.8.sp,
                        ),
                        color = PompColors.InkSecondary,
                    )
                }

                Spacer(Modifier.width(10.dp))

                Surface(
                    color = PompColors.Cinnabar,
                    shape = RoundedCornerShape(12.dp),
                ) {
                    Text(
                        text = stringResource(
                            if (done) R.string.course_foundation_repeat
                            else R.string.course_foundation_start,
                        ),
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                        ),
                        color = PompColors.Paper,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                    )
                }
            }
        }
    }
}
