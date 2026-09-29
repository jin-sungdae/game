// QA-only ScreenCaptureKit capture of one named LUMA window, never the desktop.
import AppKit
import ScreenCaptureKit
import CoreImage
import CoreMedia

final class Frames: NSObject, SCStreamOutput, @unchecked Sendable {
    let directory: URL
    let context = CIContext()
    var rows: [[String: Any]] = []
    init(_ directory: URL) { self.directory = directory }
    func stream(_ stream: SCStream, didOutputSampleBuffer sample: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, sample.isValid,
              let attachments = CMSampleBufferGetSampleAttachmentsArray(sample, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let status = attachments.first?[.status] as? Int, status == SCFrameStatus.complete.rawValue,
              let buffer = sample.imageBuffer,
              let image = context.createCGImage(CIImage(cvPixelBuffer: buffer), from: CGRect(x: 0,y: 0,width: CVPixelBufferGetWidth(buffer),height: CVPixelBufferGetHeight(buffer))) else { return }
        let name = String(format: "frame-%05d.png", rows.count)
        let rep = NSBitmapImageRep(cgImage: image)
        guard let bytes = rep.representation(using: .png, properties: [:]) else { return }
        do { try bytes.write(to: directory.appendingPathComponent(name)) } catch { return }
        rows.append(["file": name, "pts": CMTimeGetSeconds(sample.presentationTimeStamp), "wallTime": Date().timeIntervalSince1970, "width": image.width, "height": image.height])
    }
}
@main struct RecordWindow {
    static func main() async throws {
        _ = NSApplication.shared
        let args = CommandLine.arguments
        guard (args.count == 4 || args.count == 5), let pid = Int32(args[1]), let duration = Double(args[2]), duration >= 5 else { fatalError("record_window PID SECONDS OUTPUT") }
        let entity = args.count == 5 ? args[4] : "moa"
        let dir = URL(fileURLWithPath: args[3]); try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
        guard let window = content.windows.first(where: { $0.owningApplication?.processID == pid && $0.title == entity }) else { fatalError("MOA window not found") }
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let config = SCStreamConfiguration()
        config.width = Int(window.frame.width * 2); config.height = Int(window.frame.height * 2)
        config.minimumFrameInterval = CMTime(value: 1, timescale: 60)
        config.queueDepth = 8; config.showsCursor = false; config.capturesAudio = false
        config.ignoreShadowsSingleWindow = true
        let output = Frames(dir); let queue = DispatchQueue(label: "luma.qa.capture")
        let stream = SCStream(filter: filter, configuration: config, delegate: nil)
        try stream.addStreamOutput(output, type: .screen, sampleHandlerQueue: queue)
        try await stream.startCapture()
        let deadline = Date().addingTimeInterval(duration)
        while Date() < deadline && !FileManager.default.fileExists(atPath: dir.appendingPathComponent("stop").path) {
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        try await stream.stopCapture()
        queue.sync {}
        let data = try JSONSerialization.data(withJSONObject: ["pid": pid, "windowId": window.windowID, "requestedSeconds": duration, "frames": output.rows], options: [.prettyPrinted, .sortedKeys])
        try data.write(to: dir.appendingPathComponent("frames.json"))
        print("Captured \(output.rows.count) actual window frames")
    }
}
