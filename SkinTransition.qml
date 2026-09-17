import QtQuick
import QtQuick.Effects

Item {
    id: transition
    objectName: "skinTransition"
    required property Item target
    required property bool artReady
    property string phase: ""
    property string pendingSkin: ""
    property point origin: Qt.point(0, 0)
    property real revealRadius: 0
    readonly property real fullRadius: Math.hypot(Math.max(origin.x, width - origin.x),
                                                 Math.max(origin.y, height - origin.y)) + 2
    readonly property bool busy: phase !== ""
    visible: busy

    function switchFrom(button) {
        // One snapshot at a time; repeated clicks never stack full-window textures.
        if (busy) return
        pendingSkin = uiTheme.nextKey
        if (!bridge.motionEnabled) {
            uiTheme.select(pendingSkin)
            pendingSkin = ""
            return
        }
        origin = button.mapToItem(transition, button.width / 2, button.height / 2)
        revealRadius = 0
        uiTheme.transitioning = true
        phase = "capturing"
        snapshot.scheduleUpdate()
        watchdog.restart()
    }

    function reveal() {
        if (phase !== "loading" || !artReady) return
        watchdog.stop()
        phase = "revealing"
        wave.start()
    }

    function finish() {
        wave.stop()
        watchdog.stop()
        // A resize/reduced-motion event can arrive before the snapshot callback.
        if (pendingSkin) uiTheme.select(pendingSkin)
        pendingSkin = ""
        phase = ""
        uiTheme.transitioning = false
    }

    onArtReadyChanged: reveal()
    onWidthChanged: if (busy) finish()
    onHeightChanged: if (busy) finish()
    Connections {
        target: bridge
        function onMotionChanged() { if (!bridge.motionEnabled && transition.busy) transition.finish() }
    }
    ShaderEffectSource {
        id: snapshot
        sourceItem: transition.busy ? transition.target : null
        anchors.fill: parent
        live: false
        visible: false
        onScheduledUpdateCompleted: {
            if (transition.phase !== "capturing") return
            transition.phase = "loading"
            const skin = transition.pendingSkin
            transition.pendingSkin = ""
            if (!uiTheme.select(skin)) { transition.finish(); return }
            Qt.callLater(transition.reveal)
        }
    }
    Item {
        id: mask
        anchors.fill: parent
        Rectangle {
            x: transition.origin.x - transition.revealRadius
            y: transition.origin.y - transition.revealRadius
            width: transition.revealRadius * 2
            height: width
            radius: width / 2
            color: "white"
            antialiasing: true
        }
    }
    ShaderEffectSource {
        id: maskTexture
        anchors.fill: parent
        sourceItem: transition.busy ? mask : null
        hideSource: true
        visible: false
    }
    MultiEffect {
        anchors.fill: parent
        visible: transition.busy
        source: snapshot
        maskEnabled: true
        maskSource: maskTexture
        maskInverted: true
        maskThresholdMin: 0.5
        maskSpreadAtMin: 1
    }
    NumberAnimation {
        id: wave
        objectName: "skinWave"
        target: transition
        property: "revealRadius"
        from: 0
        to: transition.fullRadius
        duration: 560
        easing.type: Easing.InOutCubic
        onFinished: transition.finish()
    }
    // Never leave an old frame over the UI after a failed image/render callback.
    Timer { id: watchdog; interval: 2500; onTriggered: transition.finish() }
}
