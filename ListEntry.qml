import QtQuick
import QtQuick.Controls

ItemDelegate {
    id:entry
    padding:10
    hoverEnabled:true
    contentItem:Text {
        text:entry.text
        textFormat:Text.PlainText
        font:entry.font
        color:entry.enabled?uiTheme.current.colors.ink:uiTheme.current.colors.disabledText
        wrapMode:Text.Wrap
        maximumLineCount:3
        elide:Text.ElideRight
        verticalAlignment:Text.AlignVCenter
    }
    background:Rectangle {
        radius:10
        color:entry.highlighted?uiTheme.current.colors.selection:entry.hovered||entry.down?uiTheme.current.colors.listHover:"transparent"
        border.width:entry.activeFocus?2:0
        border.color:uiTheme.current.colors.primary
        Behavior on color { ColorAnimation { duration:bridge.motionEnabled&&!uiTheme.transitioning?110:0 } }
    }
}
