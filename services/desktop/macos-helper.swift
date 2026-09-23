// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Bounded native macOS observation and input. JSON on stdin/stdout only.
import AppKit
import ApplicationServices
import Carbon
import ScreenCaptureKit

struct Refusal: Error, LocalizedError {
    let message: String
    var errorDescription: String? { message }
}
func refuse(_ message: String) throws -> Never { throw Refusal(message: message) }
func attribute(_ element: AXUIElement, _ name: CFString) -> CFTypeRef? {
    var value: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, name, &value) == .success ? value : nil
}
func rect(_ value: CGRect) -> [String: Double] {
    ["x":value.origin.x,"y":value.origin.y,"width":value.width,"height":value.height]
}
func permissions() -> [String: Bool] {
    ["screenRecording":CGPreflightScreenCaptureAccess(),"accessibility":AXIsProcessTrusted()]
}
func displays() throws -> [CGDirectDisplayID] {
    var count: UInt32 = 0
    guard CGGetActiveDisplayList(0, nil, &count) == .success else { try refuse("Cannot inspect displays.") }
    var result = [CGDirectDisplayID](repeating:0, count:Int(count))
    guard CGGetActiveDisplayList(count, &result, &count) == .success else { try refuse("Display configuration changed.") }
    return Array(result.prefix(Int(count)))
}
func focus(_ pid: pid_t) throws -> [String: Any] {
    let app = AXUIElementCreateApplication(pid)
    AXUIElementSetMessagingTimeout(app, 0.5)
    guard let raw = attribute(app, kAXFocusedUIElementAttribute as CFString), CFGetTypeID(raw)==AXUIElementGetTypeID() else {
        try refuse("The focused control is not accessible. No keyboard input was sent.")
    }
    let element = raw as! AXUIElement
    let role = attribute(element, kAXRoleAttribute as CFString) as? String ?? ""
    let subrole = attribute(element, kAXSubroleAttribute as CFString) as? String ?? ""
    if subrole == "AXSecureTextField" || IsSecureEventInputEnabled() { try refuse("Secure input is unavailable.") }
    var path = [Int]()
    var current = element
    for _ in 0..<24 {
        if CFEqual(current, app) { return ["role":role,"subrole":subrole,"path":path.reversed().map{$0}] }
        guard let parentRaw=attribute(current,kAXParentAttribute as CFString), CFGetTypeID(parentRaw)==AXUIElementGetTypeID() else { break }
        let parent=parentRaw as! AXUIElement
        guard let children=attribute(parent,kAXChildrenAttribute as CFString) as? [AXUIElement],
              children.count<=2000, let index=children.firstIndex(where:{CFEqual($0,current)}) else { break }
        path.append(index);current=parent
    }
    try refuse("The focused control has no stable accessibility path.")
}
func scene() throws -> [String: Any] {
    guard AXIsProcessTrusted() else { try refuse("Allow Accessibility for Augmentor Desktop Control in System Settings.") }
    guard let app=NSWorkspace.shared.frontmostApplication,
          !["com.apple.loginwindow","com.apple.ScreenSaver.Engine"].contains(app.bundleIdentifier ?? "") else {
        try refuse("Unlock the screen and activate the intended application.")
    }
    let screens=try displays()
    guard screens.count==1 else { try refuse("This macOS preview requires one active display.") }
    guard let rows=CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]],
          let index=rows.firstIndex(where:{($0[kCGWindowOwnerPID as String] as? Int)==Int(app.processIdentifier) && ($0[kCGWindowLayer as String] as? Int)==0}) else {
        try refuse("The active application has no observable window.")
    }
    func window(_ row:[String:Any]) throws -> [String:Any] {
        guard let raw=row[kCGWindowBounds as String] as? [String:Any],
              let bounds=CGRect(dictionaryRepresentation:raw as CFDictionary) else { try refuse("Window geometry is unavailable.") }
        return ["id":row[kCGWindowNumber as String] as? Int ?? -1,
                "pid":row[kCGWindowOwnerPID as String] as? Int ?? -1,"geometry":rect(bounds)]
    }
    return ["window":try window(rows[index]),"above":try rows.prefix(index).filter{($0[kCGWindowAlpha as String] as? Double ?? 1)>0}.map(window),
            "screens":screens.map{["id":Int($0),"geometry":rect(CGDisplayBounds($0))]},
            "focus":(try? focus(app.processIdentifier)) ?? [:]]
}
func equal(_ a:[String:Any],_ b:[String:Any]) -> Bool {
    NSDictionary(dictionary:a).isEqual(to:b)
}
func verify(_ request:[String:Any], keyboard:Bool) throws -> [String:Any] {
    guard let grant=request["authorizationFile"] as? String,
          let info=try? FileManager.default.attributesOfItem(atPath:grant),
          info[.type] as? FileAttributeType == .typeRegular,
          (info[.ownerAccountID] as? NSNumber)?.uint32Value == getuid(),
          (info[.posixPermissions] as? NSNumber)?.intValue == 0o600,
          CGPreflightScreenCaptureAccess() else { try refuse("Desktop authorization was revoked. No input was sent.") }
    guard let expected=request["scene"] as? [String:Any] else { try refuse("Missing observed target.") }
    let current=try scene()
    guard equal(expected,current) else { try refuse("Window, focus or display changed. Observe again; no input was sent.") }
    if keyboard {
        guard let f=current["focus"] as? [String:Any], f["path"] != nil else { try refuse("The focused control is not accessible.") }
        if IsSecureEventInputEnabled() { try refuse("Secure input is unavailable.") }
    }
    return current
}
let keys:[String:CGKeyCode]=["CTRL":59,"SHIFT":56,"ALT":58,"CMD":55,"ENTER":36,"TAB":48,"ESC":53,"BACKSPACE":51,"DELETE":117,
    "LEFT":123,"RIGHT":124,"DOWN":125,"UP":126,"HOME":115,"END":119,"PAGEUP":116,"PAGEDOWN":121,"SPACE":49,
    "A":0,"S":1,"D":2,"F":3,"H":4,"G":5,"Z":6,"X":7,"C":8,"V":9,"B":11,"Q":12,"W":13,"E":14,"R":15,"Y":16,"T":17,
    "O":31,"U":32,"I":34,"P":35,"L":37,"J":38,"K":40,"N":45,"M":46]
func emitKey(_ code:CGKeyCode,_ flags:CGEventFlags = []) throws {
    guard let down=CGEvent(keyboardEventSource:nil,virtualKey:code,keyDown:true),
          let up=CGEvent(keyboardEventSource:nil,virtualKey:code,keyDown:false) else { try refuse("Could not create keyboard events.") }
    down.flags=flags;up.flags=[]
    down.post(tap:.cghidEventTap);up.post(tap:.cghidEventTap)
}
func action(_ request:[String:Any]) throws -> [String:Any] {
    let kind=request["kind"] as? String ?? ""
    let current=try verify(request,keyboard:kind != "click")
    if kind=="click" {
        guard let x=request["x"] as? Double,let y=request["y"] as? Double,x.isFinite,y.isFinite,
              let window=current["window"] as? [String:Any],let geometry=window["geometry"] as? [String:Double] else { try refuse("Invalid click target.") }
        func contains(_ g:[String:Double])->Bool { x>=g["x"]! && y>=g["y"]! && x<g["x"]!+g["width"]! && y<g["y"]!+g["height"]! }
        guard contains(geometry) else { try refuse("Point is outside the active window.") }
        for row in current["above"] as? [[String:Any]] ?? [] {
            if let g=row["geometry"] as? [String:Double],contains(g) { try refuse("Another window covers the click target.") }
        }
        guard let down=CGEvent(mouseEventSource:nil,mouseType:.leftMouseDown,mouseCursorPosition:CGPoint(x:x,y:y),mouseButton:.left),
              let up=CGEvent(mouseEventSource:nil,mouseType:.leftMouseUp,mouseCursorPosition:CGPoint(x:x,y:y),mouseButton:.left) else { try refuse("Could not create pointer event.") }
        _=try verify(request,keyboard:false)
        down.post(tap:.cghidEventTap);up.post(tap:.cghidEventTap)
    } else if kind=="key" {
        guard let names=request["keys"] as? [String],(1...3).contains(names.count),Set(names).count==names.count,
              names.allSatisfy({keys[$0] != nil}),names.dropLast().allSatisfy({["CTRL","ALT","SHIFT","CMD"].contains($0)}),
              !["CTRL","ALT","SHIFT","CMD"].contains(names.last!) else { try refuse("Invalid key chord.") }
        var flags:CGEventFlags=[]
        for name in names.dropLast() {
            flags.formUnion(["CTRL":.maskControl,"ALT":.maskAlternate,"SHIFT":.maskShift,"CMD":.maskCommand][name]!)
        }
        // A single down/up pair carries modifier flags; no modifier is left held.
        let code=keys[names.last!]!
        _=try verify(request,keyboard:true)
        try emitKey(code,flags)
    } else if kind=="text" {
        guard let text=request["text"] as? String,text.count==1,!text.unicodeScalars.contains(where:{$0.value<32 && $0.value != 10}) else { try refuse("Expected one printable character.") }
        if text=="\n" { _=try verify(request,keyboard:true);try emitKey(36) }
        else {
            let units=Array(text.utf16)
            guard let down=CGEvent(keyboardEventSource:nil,virtualKey:0,keyDown:true),
                  let up=CGEvent(keyboardEventSource:nil,virtualKey:0,keyDown:false) else { try refuse("Could not create text events.") }
            for event in [down,up] {
                event.keyboardSetUnicodeString(stringLength:units.count,unicodeString:units)
            }
            _=try verify(request,keyboard:true)
            down.post(tap:.cghidEventTap);up.post(tap:.cghidEventTap)
        }
    } else { try refuse("Unsupported input operation.") }
    return ["dispatched":true,"verified":false]
}

@main struct DesktopHelper {
    static func main() async {
        do {
            let data=FileHandle.standardInput.readDataToEndOfFile()
            guard data.count<=32768,let request=try JSONSerialization.jsonObject(with:data) as? [String:Any] else { try refuse("Invalid request.") }
            let method=request["method"] as? String ?? ""
            var result:[String:Any]
            switch method {
            case "status": result=["permissions":permissions(),"backend":"macos-screencapturekit","displays":try displays().count]
            case "requestPermissions":
                _=AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String:true] as CFDictionary)
                if !CGPreflightScreenCaptureAccess() { _=CGRequestScreenCaptureAccess() }
                result=["permissions":permissions()]
            case "scene": result=try scene()
            case "observe":
                if let pid=request["appPid"] as? Int32 {
                    guard pid>0,AXIsProcessTrusted() else { try refuse("Allow Accessibility before inspecting application controls.") }
                    let app=AXUIElementCreateApplication(pid)
                    AXUIElementSetMessagingTimeout(app,0.5)
                    var stack:[(AXUIElement,[Int],Int)]=[(app,[],0)]
                    var nodes=[[String:Any]]()
                    let deadline=Date().addingTimeInterval(5)
                    while let (node,path,depth)=stack.popLast(),nodes.count<120,Date()<deadline {
                        let role=attribute(node,kAXRoleAttribute as CFString) as? String ?? "unknown"
                        let secure=(attribute(node,kAXSubroleAttribute as CFString) as? String)=="AXSecureTextField"
                        let title=secure ? "[password field]" : String((attribute(node,kAXTitleAttribute as CFString) as? String ?? "").prefix(300))
                        nodes.append(["path":path,"role":role,"name":title])
                        if depth<8 && !secure,let children=attribute(node,kAXChildrenAttribute as CFString) as? [AXUIElement] {
                            for (index,child) in children.prefix(100).enumerated().reversed() { stack.append((child,path+[index],depth+1)) }
                        }
                    }
                    result=["appPid":pid,"nodes":nodes,"truncated":!stack.isEmpty || nodes.count>=120 || Date()>=deadline]
                } else {
                    result=["applications":NSWorkspace.shared.runningApplications.filter{$0.activationPolicy == .regular}.prefix(200).map{
                        ["pid":Int($0.processIdentifier),"name":$0.localizedName ?? "Application"] as [String:Any]},"coverage":"macOS regular applications"]
                }
            case "capture":
                guard CGPreflightScreenCaptureAccess() else { try refuse("Allow Screen Recording for Augmentor Desktop Control in System Settings.") }
                let before=try scene()
                let available=try await SCShareableContent.excludingDesktopWindows(true,onScreenWindowsOnly:true)
                guard let display=available.displays.first(where:{$0.displayID==CGMainDisplayID()}) else { try refuse("Shared display is unavailable.") }
                let filter=SCContentFilter(display:display,excludingWindows:[])
                let config=SCStreamConfiguration()
                let ratio=min(1.0,min(1600.0/Double(display.width),1200.0/Double(display.height)))
                config.width=max(1,Int(Double(display.width)*ratio));config.height=max(1,Int(Double(display.height)*ratio));config.showsCursor=false
                let image=try await SCScreenshotManager.captureImage(contentFilter:filter,configuration:config)
                guard equal(before,try scene()) else { try refuse("Target changed during capture. Observe again.") }
                let bitmap=NSBitmapImageRep(cgImage:image)
                guard let jpeg=bitmap.representation(using:.jpeg,properties:[.compressionFactor:0.8]),jpeg.count<=900000 else { try refuse("Screenshot exceeds the preview limit.") }
                result=["scene":before,"image":["data":jpeg.base64EncodedString(),"mimeType":"image/jpeg","width":image.width,"height":image.height]]
            case "action": result=try action(request)
            default: try refuse("Unsupported macOS operation.")
            }
            let output=try JSONSerialization.data(withJSONObject:["ok":true,"result":result],options:[.sortedKeys])
            FileHandle.standardOutput.write(output);FileHandle.standardOutput.write(Data([10]))
        } catch {
            let output=(try? JSONSerialization.data(withJSONObject:["ok":false,"error":String(error.localizedDescription.prefix(600))])) ?? Data()
            FileHandle.standardOutput.write(output);FileHandle.standardOutput.write(Data([10]))
        }
    }
}
