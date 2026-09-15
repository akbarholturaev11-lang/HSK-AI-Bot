# kotlinx.serialization keeps its generated serializers via companion objects.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**

-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}

-if @kotlinx.serialization.Serializable class **
-keepclassmembers class <1> {
    static <1>$Companion Companion;
    static **$* *;
}
-if @kotlinx.serialization.Serializable class **$*
-keepclassmembers class <1>$<2> {
    kotlinx.serialization.KSerializer serializer(...);
}

# Retrofit interfaces are referenced reflectively.
-keep,allowobfuscation,allowshrinking interface retrofit2.Call
-keep,allowobfuscation,allowshrinking class retrofit2.Response
-keep,allowobfuscation,allowshrinking class kotlin.coroutines.Continuation

# OkHttp / Okio platform lookups.
-dontwarn okhttp3.internal.platform.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**

# Never let obfuscation rename Glance widget receivers declared in the manifest.
-keep class com.pomp.hskai.widget.** { *; }

# Retrofit javob modeli — maydonlarini hech kim o'qimasa ham KERAK.
#
# Retrofit javob turini metodning generic imzosidan o'qiydi va
# kotlinx.serialization uning serializerini reflectiv topadi. R8 esa
# "hech kim o'qimayapti" deb klassning O'ZINI olib tashlaydi: 1.1.0 da
# shunday oltita model yo'qolgan (`DrillGateResponse` shular ichida), va
# ularni qaytaradigan har bir so'rov TARMOQQA CHIQMASDAN yiqilgan —
# "Ieroglif tanish" va "Talaffuz mashqi" telefonda aynan shuning uchun
# "Kutilmagan xatolik" bergan.
#
# `allowobfuscation` — nom o'zgarishi mumkin (APK kichik qoladi), lekin
# klass o'chirilmaydi va optimizatsiya uni boshqasiga qo'shib yubormaydi.
# DIQQAT: bu yerda `-if` ishlamaydi. R8 da `-if` sharti FAQAT allaqachon
# "tirik" deb topilgan klassga qaraladi — o'chirilgan klassni u qaytara
# olmaydi. Shuning uchun shart emas, to'g'ridan-to'g'ri saqlash kerak.
-keep,allowobfuscation @kotlinx.serialization.Serializable class ** {
    *;
}
