import QtQuick
import QtQuick.Controls

TabButton {
    id:tab
    implicitHeight:34
    leftPadding:14
    rightPadding:14
    font.weight:checked?Font.DemiBold:Font.Normal
    contentItem:Text { text:tab.text; textFormat:Text.PlainText; font:tab.font; color:tab.enabled?uiTheme.current.colors.selectionInk:uiTheme.current.colors.disabledInk; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter; elide:Text.ElideRight }
    background:Rectangle {
        radius:8
        color:tab.checked?uiTheme.current.colors.control:tab.hovered?uiTheme.current.colors.segmentHover:"transparent"
        border.color:tab.activeFocus?uiTheme.current.colors.primary:uiTheme.current.colors.segmentBorder
        border.width:tab.activeFocus?2:tab.checked?1:0
        Behavior on color { ColorAnimation { duration:bridge.motionEnabled&&!uiTheme.transitioning?120:0 } }
    }
}
