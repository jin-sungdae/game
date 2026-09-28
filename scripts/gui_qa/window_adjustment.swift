// QA-only, user-authorized temporary window adjustment with automatic restoration.
import AppKit
import ApplicationServices
var restoreRequested = false
signal(SIGTERM) { _ in restoreRequested = true }
signal(SIGINT) { _ in restoreRequested = true }
func attr(_ w:AXUIElement,_ key:String)->CFTypeRef? { var v:CFTypeRef?; return AXUIElementCopyAttributeValue(w,key as CFString,&v) == .success ? v:nil }
func point(_ w:AXUIElement)->CGPoint { var p=CGPoint.zero; if let v=attr(w,kAXPositionAttribute) { AXValueGetValue(v as! AXValue,.cgPoint,&p) };return p }
func size(_ w:AXUIElement)->CGSize { var p=CGSize.zero; if let v=attr(w,kAXSizeAttribute) { AXValueGetValue(v as! AXValue,.cgSize,&p) };return p }
func state(_ w:AXUIElement)->[String:Any] { let p=point(w),s=size(w);return ["x":p.x,"y":p.y,"width":s.width,"height":s.height,"fullscreen":(attr(w,"AXFullScreen") as? NSNumber)?.boolValue ?? false] }
func geometry(_ w:AXUIElement,_ p:CGPoint,_ s:CGSize) { var p=p,s=s; AXUIElementSetAttributeValue(w,kAXPositionAttribute as CFString,AXValueCreate(.cgPoint,&p)!);AXUIElementSetAttributeValue(w,kAXSizeAttribute as CFString,AXValueCreate(.cgSize,&s)!) }
let args=CommandLine.arguments
if args.count != 6 { fatalError("PID X Y TEMP_HEIGHT OUTPUT_DIRECTORY") }
let pid=Int32(args[1])!,x=Double(args[2])!,y=Double(args[3])!,height=Double(args[4])!,dir=URL(fileURLWithPath:args[5]);try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
let app=AXUIElementCreateApplication(pid)
let windows=attr(app,kAXWindowsAttribute) as? [AXUIElement] ?? []
guard let window=windows.first(where:{abs(point($0).x-x)<3 && abs(point($0).y-y)<3 && size($0).height>100}) else {fatalError("Exact observed window not found")}
let original=state(window),originalPoint=point(window),originalSize=size(window),full=(original["fullscreen"] as! Bool)
var report:[String:Any]=["pid":pid,"original":original,"startedAt":Date().timeIntervalSince1970]
func save() {try? JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("window-state.json"))}
save()
func run() {
 defer {
  geometry(window,originalPoint,originalSize)
  if full {AXUIElementSetAttributeValue(window,"AXFullScreen" as CFString,kCFBooleanTrue);Thread.sleep(forTimeInterval:2)}
  geometry(window,originalPoint,originalSize)
  Thread.sleep(forTimeInterval:0.3)
  report["restored"]=state(window);report["endedAt"]=Date().timeIntervalSince1970;report["restoreMatchesOriginal"]=NSDictionary(dictionary:original).isEqual(to:state(window));save()
 }
 if full {let result=AXUIElementSetAttributeValue(window,"AXFullScreen" as CFString,kCFBooleanFalse);if result != .success {report["error"]="Cannot leave fullscreen";return};Thread.sleep(forTimeInterval:2)}
 geometry(window,originalPoint,CGSize(width:originalSize.width,height:height));Thread.sleep(forTimeInterval:0.5);report["temporary"]=state(window);save()
 let deadline=Date().addingTimeInterval(600)
 while Date()<deadline && !restoreRequested && !FileManager.default.fileExists(atPath:dir.appendingPathComponent("restore").path) {Thread.sleep(forTimeInterval:0.2)}
}
run()
