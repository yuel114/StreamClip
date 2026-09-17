import QtQuick
import QtQuick.Effects

Item {
    id: artwork
    property alias source: image.source
    property alias fillMode: image.fillMode
    property alias horizontalAlignment: image.horizontalAlignment
    readonly property int status: image.status
    property real radius: 16
    Image {
        id: image
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        visible: false
    }
    Rectangle {
        id: mask
        anchors.fill: parent
        radius: artwork.radius
        layer.enabled: true
        visible: false
    }
    MultiEffect {
        anchors.fill: parent
        source: image
        maskEnabled: true
        maskSource: mask
    }
}
