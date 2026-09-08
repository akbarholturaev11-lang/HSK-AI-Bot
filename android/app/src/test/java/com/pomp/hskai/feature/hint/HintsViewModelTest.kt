package com.pomp.hskai.feature.hint

import com.pomp.hskai.data.api.AndroidHintDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HintsViewModelTest {

    private val dispatcher = StandardTestDispatcher()
    private val dismissed = mutableListOf<String>()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun model() = HintsViewModel { key -> dismissed += key }

    private fun hint(key: String, section: String = "mashq") =
        AndroidHintDto(key = key, title = key, body = "b", section = section)

    @Test
    fun `what the server sent is what is shown`() = runTest(dispatcher) {
        val model = model()

        model.onMapLoaded(listOf(hint("a"), hint("b")))

        assertEquals(listOf("a", "b"), model.hints.value.map { it.key })
    }

    @Test
    fun `a closed block goes at once and is reported`() = runTest(dispatcher) {
        val model = model()
        model.onMapLoaded(listOf(hint("a"), hint("b")))

        model.dismiss("a")

        // Gone before the write finishes: the learner pressed X, and waiting
        // for a round trip reads as the button not having worked.
        assertEquals(listOf("b"), model.hints.value.map { it.key })
        advanceUntilIdle()
        assertEquals(listOf("a"), dismissed)
    }

    @Test
    fun `a block closed here does not come back with the next map`() = runTest(dispatcher) {
        // The write may still be in flight when the map is re-read, so the
        // server can legitimately send the block again. It must not reappear.
        val model = model()
        model.onMapLoaded(listOf(hint("a"), hint("b")))
        model.dismiss("a")

        model.onMapLoaded(listOf(hint("a"), hint("b")))

        assertEquals(listOf("b"), model.hints.value.map { it.key })
    }

    @Test
    fun `closing the same block twice is reported once`() = runTest(dispatcher) {
        val model = model()
        model.onMapLoaded(listOf(hint("a")))

        model.dismiss("a")
        model.dismiss("a")
        advanceUntilIdle()

        assertEquals(listOf("a"), dismissed)
    }

    @Test
    fun `a block with no key is dropped rather than drawn`() = runTest(dispatcher) {
        // A keyless block could never be closed, so it would sit there for good.
        val model = model()

        model.onMapLoaded(listOf(hint(""), hint("a")))

        assertEquals(listOf("a"), model.hints.value.map { it.key })
    }
}
