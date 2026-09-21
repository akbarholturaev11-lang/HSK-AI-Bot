import AVFoundation
import Foundation

@MainActor
final class MandarinAudioRecorder {
    private var recorder: AVAudioRecorder?
    private var url: URL?

    func requestPermission() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }

    func start() throws {
        cancel()
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .spokenAudio, options: [.defaultToSpeaker])
        try session.setActive(true, options: .notifyOthersOnDeactivation)

        let fileURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("hsk-pronunciation-\(UUID().uuidString).m4a")
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44_100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
        ]
        let recorder = try AVAudioRecorder(url: fileURL, settings: settings)
        recorder.prepareToRecord()
        guard recorder.record() else { throw MandarinAudioRecorderError.couldNotStart }
        self.recorder = recorder
        self.url = fileURL
    }

    func stopDataURL() throws -> String {
        guard let recorder, let url else { throw MandarinAudioRecorderError.notRecording }
        recorder.stop()
        self.recorder = nil
        self.url = nil
        defer {
            try? FileManager.default.removeItem(at: url)
            try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        }
        let data = try Data(contentsOf: url)
        guard !data.isEmpty else { throw MandarinAudioRecorderError.emptyRecording }
        return "data:audio/mp4;base64,\(data.base64EncodedString())"
    }

    func cancel() {
        recorder?.stop()
        recorder = nil
        if let url { try? FileManager.default.removeItem(at: url) }
        url = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    deinit {
        recorder?.stop()
        if let url { try? FileManager.default.removeItem(at: url) }
    }
}

enum MandarinAudioRecorderError: Error {
    case couldNotStart
    case notRecording
    case emptyRecording
}
