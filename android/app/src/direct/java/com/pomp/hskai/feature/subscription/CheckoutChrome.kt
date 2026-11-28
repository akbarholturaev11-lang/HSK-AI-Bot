package com.pomp.hskai.feature.subscription

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.HeadsetMic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.animation.core.animateFloat
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.ProColors

/** PWA checkout toolbar, with native 48dp hit targets and one navigation action. */
@Composable
internal fun CheckoutHeader(firstStep: Boolean, onNavigate: () -> Unit, onSupport: () -> Unit,
    title: String = stringResource(R.string.checkout_heading), enabled: Boolean = true) {
    Box(Modifier.fillMaxWidth().heightIn(min = 48.dp).testTag("checkout-header")) {
        Text(title, color = ProColors.Ink, fontSize = 24.sp, lineHeight = 28.sp,
            fontWeight = FontWeight.Black, textAlign = TextAlign.Center,
            modifier = Modifier.align(Alignment.Center).fillMaxWidth().padding(horizontal = 52.dp)
                .testTag("checkout-title"))
        IconButton(onClick = onNavigate, enabled = enabled,
            modifier = Modifier.align(Alignment.CenterStart).size(48.dp).testTag("checkout-navigation")) {
            Icon(if (firstStep) Icons.Default.Close else Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = stringResource(if (firstStep) R.string.action_close else R.string.action_back),
                tint = ProColors.Muted, modifier = Modifier.size(24.dp))
        }
        IconButton(onClick = onSupport,
            modifier = Modifier.align(Alignment.CenterEnd).size(48.dp).testTag("checkout-support")) {
            Icon(Icons.Default.HeadsetMic, contentDescription = stringResource(R.string.sub_help_title),
                tint = ProColors.Muted, modifier = Modifier.size(22.dp))
        }
    }
}

@Composable
internal fun CheckoutProgress(step: Int, count: Int) {
    Row(Modifier.fillMaxWidth().padding(vertical = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        repeat(count) { index ->
            Box(Modifier.weight(1f).height(4.dp).background(
                if (index <= step) ProColors.Cta else ProColors.Line, CircleShape))
        }
    }
}

/** Layout from iphone-pwa-inline-pro.css; actual price/reference never drives an invoice. */
@Composable
internal fun CheckoutPlanTile(title: String, amount: String, currency: String, reference: String?,
    selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier, compact: Boolean = false,
    badge: String? = null, enabled: Boolean = true) {
    Column(modifier.heightIn(min = if (compact) 112.dp else 130.dp)
        .border(if (selected) 2.dp else 1.dp, if (selected) ProColors.Cta else ProColors.Line, RoundedCornerShape(18.dp))
        .background(if (selected) PompColors.CinnabarSoft else ProColors.Surface, RoundedCornerShape(18.dp))
        .selectable(selected, enabled = enabled, role = Role.RadioButton, onClick = onClick)
        .padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, color = if (selected) ProColors.CtaDeep else ProColors.Muted,
                fontSize = 14.sp, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            if (selected) Icon(Icons.Default.Check, contentDescription = null,
                tint = ProColors.OnCta, modifier = Modifier.size(20.dp).background(ProColors.Cta, CircleShape).padding(3.dp))
        }
        badge?.let { Text(it, color = PompColors.Ink, fontSize = 11.sp, fontWeight = FontWeight.Bold,
            modifier = Modifier.border(1.dp, PompColors.Jade, CircleShape)
                .background(PompColors.JadeSoft, CircleShape).padding(horizontal = 6.dp, vertical = 2.dp)) }
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            reference?.let { Text(if (compact) it else "$it $currency", color = ProColors.Muted, fontSize = 12.sp,
                textDecoration = TextDecoration.LineThrough) }
            Text("$amount $currency", color = ProColors.Ink, fontSize = if (compact) 21.sp else 28.sp,
                lineHeight = if (compact) 25.sp else 32.sp, fontWeight = FontWeight.ExtraBold)
        }
    }
}

@Composable
internal fun CheckoutPrimary(label: String, busy: Boolean = false, enabled: Boolean = true,
    modifier: Modifier = Modifier, onClick: () -> Unit) {
    Button(onClick = onClick, enabled = enabled && !busy,
        modifier = modifier.fillMaxWidth().heightIn(min = 56.dp).drawBehind {
            if (enabled && !busy) drawRoundRect(ProColors.CtaDeep,
                topLeft = androidx.compose.ui.geometry.Offset(0f, 3.dp.toPx()),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(16.dp.toPx()))
        }, shape = RoundedCornerShape(16.dp),
        colors = ButtonDefaults.buttonColors(containerColor = ProColors.Cta, contentColor = ProColors.OnCta,
            disabledContainerColor = ProColors.Cta.copy(alpha = .45f), disabledContentColor = ProColors.OnCta.copy(alpha = .85f))) {
        if (busy) CircularProgressIndicator(Modifier.size(20.dp), color = ProColors.OnCta, strokeWidth = 2.dp)
        else Text(label, fontSize = 17.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
    }
}

@Composable
internal fun LimitOfferHero(source: String) {
    Column(Modifier.fillMaxWidth().padding(bottom = 20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        CheckoutPanda(Modifier.size(148.dp).testTag("limit-panda"))
        Text(stringResource(R.string.checkout_limit_title), color = ProColors.Ink,
            fontSize = 28.sp, lineHeight = 32.sp, fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.Center)
        Text(stringResource(R.string.checkout_limit_subtitle), color = ProColors.Muted,
            fontSize = 16.sp, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 8.dp, bottom = 20.dp))
        val benefit = when {
            source.contains("mistake") -> R.string.hsk_course_learning_pro_mistakes
            source.contains("course") || source.contains("lesson") -> R.string.hsk_course_learning_pro_lesson
            else -> R.string.checkout_benefit_lessons
        }
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(benefit, R.string.checkout_benefit_voice, R.string.checkout_benefit_ads).forEach { res ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Icon(Icons.Default.Check, null, tint = PompColors.Jade,
                        modifier = Modifier.size(22.dp).background(PompColors.JadeSoft, CircleShape).padding(4.dp))
                    Text(stringResource(res), color = ProColors.Ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

/** Exact local export of the PWA pandaSvg poses (see tools/export_checkout_panda.py).
 * The raster keeps canonical face/paws/PRO-card geometry; native breathing
 * obeys Android's remove-animations setting without a WebView/network request. */
@Composable
internal fun CheckoutPanda(modifier: Modifier = Modifier, pose: String = "pro") {
    val context = androidx.compose.ui.platform.LocalContext.current
    val motionOff = androidx.compose.runtime.remember { com.pomp.hskai.core.design.components.hskMotionOff(context) }
    val scale = if (motionOff) 1f else androidx.compose.animation.core.rememberInfiniteTransition(label = "checkout-panda")
        .animateFloat(1f, 1.02f, androidx.compose.animation.core.infiniteRepeatable(
            androidx.compose.animation.core.tween(1300), androidx.compose.animation.core.RepeatMode.Reverse), label = "breathing").value
    Box(modifier, contentAlignment = Alignment.Center) {
        androidx.compose.foundation.Canvas(Modifier.fillMaxSize()) {
            drawCircle(androidx.compose.ui.graphics.Brush.radialGradient(
                listOf(ProColors.Halo, androidx.compose.ui.graphics.Color.Transparent), radius = size.minDimension * .48f))
        }
        androidx.compose.foundation.Image(androidx.compose.ui.res.painterResource(when (pose) {
            "read" -> R.drawable.checkout_panda_read
            "celebrate" -> R.drawable.checkout_panda_celebrate
            else -> R.drawable.checkout_panda_pro
        }), contentDescription = null, modifier = Modifier.size(118.dp, 122.dp)
            .graphicsLayer { scaleY = scale })
    }
}

@Composable
internal fun CheckoutRegionButton(label: String, onClick: () -> Unit, enabled: Boolean = true) {
    OutlinedButton(onClick = onClick, enabled = enabled, shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, ProColors.Line),
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
        Text(label, color = ProColors.Muted, fontSize = 16.sp, fontWeight = FontWeight.Normal,
            modifier = Modifier.weight(1f))
        Icon(Icons.Default.KeyboardArrowDown, null, tint = ProColors.Muted, modifier = Modifier.size(20.dp))
    }
}

internal fun checkoutCountryLabelId(region: String): Int = when (region) {
    "tj" -> R.string.checkout_country_tj
    "uz" -> R.string.checkout_country_uz
    "ru" -> R.string.checkout_country_ru
    "cn" -> R.string.checkout_country_cn
    else -> R.string.checkout_country_other
}

/** Native equivalent of the PWA .hip-region select: short country label,
 * left flag, right chevron, and the same ordered selectable country list. */
@Composable
internal fun CheckoutCountrySelector(region: String, regions: List<String>, onSelect: (String) -> Unit,
    enabled: Boolean = true) {
    var expanded by remember { mutableStateOf(false) }
    BoxWithConstraints(Modifier.fillMaxWidth().testTag("checkout-country")) {
        val menuWidth = maxWidth
        CheckoutRegionButton("${REGION_FLAGS[region].orEmpty()} ${stringResource(checkoutCountryLabelId(region))}",
            onClick = { expanded = true }, enabled = enabled && regions.isNotEmpty())
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false },
            modifier = Modifier.width(menuWidth), containerColor = ProColors.Surface) {
            regions.forEach { choice ->
                DropdownMenuItem(text = {
                    Text("${REGION_FLAGS[choice].orEmpty()} ${stringResource(checkoutCountryLabelId(choice))}",
                        color = ProColors.Ink, fontSize = 16.sp)
                }, trailingIcon = {
                    if (choice == region) Icon(Icons.Default.Check, null, tint = ProColors.Cta)
                }, onClick = { expanded = false; onSelect(choice) })
            }
        }
    }
}
