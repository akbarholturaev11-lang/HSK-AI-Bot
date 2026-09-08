package com.pomp.hskai.feature.course

import kotlin.math.roundToInt
import kotlin.math.sin

/**
 * Qator balandligi.
 *
 * Mini App'da qator 84px va yozuv keyingi qatorning bo'sh joyiga chiqib
 * ketadi — HTML'da hech nima kesilmaydi. Compose'da esa qator o'lchamidan
 * oshgan ustun MARKAZLASHADI: tugun yuqoriga suriladi (yo'lakcha uning
 * markazidan o'tmay qoladi) va yozuvning pastki qismi kesiladi. Shuning uchun
 * bu yerda qator tugun + IKKI qatorli yozuvni to'liq sig'diradi.
 */
internal const val COURSE_PATH_ROW_HEIGHT_DP = 124f

internal const val COURSE_PATH_SWING_DP = 76f

/** Tugun qutisi — "davom etish" halqasi sig'adigan o'lcham. */
internal const val COURSE_NODE_BOX_DP = 76f

/**
 * Tugun qutisining tepasida qoldiriladigan bo'sh joy.
 *
 * "DAVOM ETISH" pufakchasi shu yerga chiqadi. Usiz u yuqoridagi tugunning
 * yozuvini butunlay yopib qo'yadi — bir marta aynan shunday bo'lgan.
 */
internal const val COURSE_NODE_TOP_GAP_DP = 10f

/**
 * Tugun markazi qatorning TEPASIDAN qancha pastda.
 *
 * Yo'lakcha aynan shu nuqtadan o'tadi — bu son tugunning haqiqiy joylashuvi
 * bilan mos kelmasa, yo'lakcha tugunning yonidan o'tib ketadi.
 */
internal const val COURSE_NODE_CENTER_DP = COURSE_NODE_TOP_GAP_DP + COURSE_NODE_BOX_DP / 2f

/**
 * Tugun ostidagi ikki qatorli yozuvning balandligi.
 *
 * Aniq son ATAYLAB: shrift metrikasiga qoldirilsa qator balandligi qurilmadan
 * qurilmaga o'zgaradi va yozuv keyingi qatorga tushib ketadi.
 */
internal const val COURSE_NODE_LABEL_DP = 28f

/** Tugunning gorizontal siljishi. Mini App'dagi `Math.sin(...)*76` ning o'zi. */
internal fun coursePathOffsetDp(unitIndex: Int, nodeIndex: Int): Float =
    (sin((unitIndex * 3 + nodeIndex) * 0.9) * COURSE_PATH_SWING_DP).roundToInt().toFloat()

/**
 * Bitta qatordagi yo'lakcha bo'lagi, QATORNING O'Z koordinatasida.
 *
 * Nega butun bo'lim uchun bitta egri chiziq emas: qatorlar `LazyColumn`
 * elementlari, ular orasida bitta rasm chiza olmaymiz. Ilgari har bir qator
 * butun chiziqni chizib, o'zidan tashqarisini kesib tashlardi — bu katta
 * ofsetlar va ularga bog'liq xatolar demak edi. Endi har bir qator faqat
 * o'ziga tegishli ikki yarim bo'g'inni chizadi:
 *
 *   • oldingi tugundan shu tugungacha (yuqoridan kirib keladi),
 *   • shu tugundan keyingisigacha (pastga chiqib ketadi).
 *
 * Qo'shni qatorlar bir xil nuqtalardan hisoblanadi, shuning uchun chegarada
 * uziq ko'rinmaydi. Va tugun markazi ta'rifan `(x, COURSE_NODE_CENTER_DP)` —
 * chiziq undan o'tmasligi mumkin emas.
 *
 * [previousXDp] / [nextXDp] `null` bo'lsa o'sha tomonda qo'shni yo'q.
 */
internal data class CourseTrailSegment(
    val startXDp: Float,
    val startYDp: Float,
    val control1XDp: Float,
    val control1YDp: Float,
    val control2XDp: Float,
    val control2YDp: Float,
    val endXDp: Float,
    val endYDp: Float,
)

internal fun courseTrailSegmentsForRow(
    previousXDp: Float?,
    currentXDp: Float,
    nextXDp: Float?,
): List<CourseTrailSegment> {
    val here = COURSE_NODE_CENTER_DP
    val above = here - COURSE_PATH_ROW_HEIGHT_DP
    val below = here + COURSE_PATH_ROW_HEIGHT_DP
    return buildList {
        if (previousXDp != null) {
            // Mini App `drawTrails`: nazorat nuqtalari ikki tugun orasidagi
            // o'rta balandlikda, ya'ni chiziq tugunga tik kirib keladi.
            val middle = (above + here) / 2f
            add(
                CourseTrailSegment(
                    startXDp = previousXDp, startYDp = above,
                    control1XDp = previousXDp, control1YDp = middle,
                    control2XDp = currentXDp, control2YDp = middle,
                    endXDp = currentXDp, endYDp = here,
                )
            )
        }
        if (nextXDp != null) {
            val middle = (here + below) / 2f
            add(
                CourseTrailSegment(
                    startXDp = currentXDp, startYDp = here,
                    control1XDp = currentXDp, control1YDp = middle,
                    control2XDp = nextXDp, control2YDp = middle,
                    endXDp = nextXDp, endYDp = below,
                )
            )
        }
    }
}
