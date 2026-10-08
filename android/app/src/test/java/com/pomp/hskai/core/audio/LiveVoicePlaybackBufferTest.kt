package com.pomp.hskai.core.audio

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LiveVoicePlaybackBufferTest {
    @Test fun aFiveSecondReplyCanArriveInABurstWithoutDroppingItsEnding() {
        val buffer = LiveVoicePlaybackBuffer()
        repeat(250) { index ->
            assertTrue(buffer.offer(ByteArray(960) { index.toByte() }))
        }
        repeat(250) { index ->
            assertArrayEquals(ByteArray(960) { index.toByte() }, buffer.take().pcm)
        }
    }

    @Test fun interruptionDiscardsTheOldReplyAndRetainsTheNewOne() {
        val buffer = LiveVoicePlaybackBuffer()
        buffer.offer(byteArrayOf(1, 2))
        val inFlight = buffer.take()
        buffer.offer(byteArrayOf(3, 4))
        buffer.clear()
        assertFalse(buffer.isCurrent(inFlight))
        val newReply = byteArrayOf(5, 6)
        assertTrue(buffer.offer(newReply))
        newReply[0] = 9
        val current = buffer.take()
        assertTrue(buffer.isCurrent(current))
        assertArrayEquals(byteArrayOf(5, 6), current.pcm)
    }

    @Test fun anOversizedReplyCannotGrowTheQueueWithoutBound() {
        val buffer = LiveVoicePlaybackBuffer()
        assertFalse(buffer.offer(ByteArray(2_000_000)))
        assertTrue(buffer.offer(ByteArray(960)))
        assertTrue(buffer.isCurrent(buffer.take()))
    }
}
