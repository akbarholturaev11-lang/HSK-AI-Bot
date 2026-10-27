package com.pomp.hskai.feature.update

import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.platform.LocalContext

/** Play-managed installs must open the listing, never a sideloaded APK. */
@Composable
fun UpdateNoticeScreen(onClose: () -> Unit) {
    val context = LocalContext.current
    LaunchedEffect(Unit) {
        val packageName = context.packageName
        val market = Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$packageName"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        val web = Intent(
            Intent.ACTION_VIEW,
            Uri.parse("https://play.google.com/store/apps/details?id=$packageName"),
        ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        val opened = runCatching { context.startActivity(market) }.isSuccess ||
            runCatching { context.startActivity(web) }.isSuccess
        if (!opened) {
            Toast.makeText(context, android.R.string.dialog_alert_title, Toast.LENGTH_SHORT).show()
        }
        onClose()
    }
}
