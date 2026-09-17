import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: form
    enabled: !bridge.busy
    property var fields: []
    property var values: ({})
    property var accounts: []
    property var models: []
    property var asrModels: []
    property bool asrModelsLoading: false
    property string asrModelsMessage: ""
    property bool dirty: false
    property string pickerKey: ""
    property string pickerKind: ""
    signal edited(string key)
    signal loadAsrModels()
    spacing: 14
    function setValue(key, value) {
        let next = Object.assign({}, values)
        next[key] = value
        values = next
        dirty = true
        edited(key)
    }
    function reset(data) { values = Object.assign({}, data); dirty = false }
    Repeater {
        model: form.fields
        delegate: ColumnLayout {
            id: row
            required property var modelData
            readonly property string key: modelData.key
            readonly property string kind: modelData.kind
            Layout.fillWidth: true
            spacing: 6
            Label { textFormat: Text.PlainText; text: row.modelData.label; font.pixelSize: 12; font.weight: Font.DemiBold; color: uiTheme.current.colors.muted; visible: row.kind !== "bool"; Layout.fillWidth: true; wrapMode: Text.Wrap }
            ToggleSwitch {
                objectName: "toggle_" + row.key
                visible: row.kind === "bool"
                text: row.modelData.label
                checked: Boolean(form.values[row.key])
                onToggled: form.setValue(row.key, checked)
                Layout.fillWidth: true
            }
            ChoiceBox {
                id: choice
                objectName: "choice_" + row.key
                Accessible.name: row.modelData.label
                visible: ["choice", "account", "model", "asr_model"].indexOf(row.kind) >= 0
                Layout.fillWidth: true
                textRole: "label"
                valueRole: "value"
                model: row.kind === "account" ? [{value:0, label:"使用全局录制账号"}].concat(form.accounts.filter(a => a.enabled && ["both","download"].indexOf(a.role)>=0).map(a => ({value:a.id,label:a.name}))) : row.kind === "asr_model" ? form.asrModels.map(m => ({value:m,label:m})) : row.kind === "model" ? form.models.map(m => ({value:m,label:m})) : (row.modelData.choices || [])
                currentIndex: {
                    for (let i=0; i<model.length; ++i) if (String(model[i].value) === String(form.values[row.key])) return i
                    return -1
                }
                onActivated: form.setValue(row.key, currentValue)
            }
            ActionButton {
                objectName: row.kind === "asr_model" ? "loadAsrModelsButton" : ""
                visible: row.kind === "asr_model"
                text: form.asrModelsLoading ? "加载中…" : "加载 ASR 模型"
                enabled: !form.asrModelsLoading
                onClicked: form.loadAsrModels()
            }
            Label {
                visible: row.kind === "asr_model" && text.length > 0
                text: form.asrModelsMessage
                textFormat: Text.PlainText
                color: uiTheme.current.colors.muted
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            ScrollView {
                visible: row.kind === "multiline"
                Layout.fillWidth: true
                Layout.preferredHeight: 115
                contentWidth: availableWidth
                TextArea {
                    id: multiline
                    Accessible.name: row.modelData.label
                    text: String(form.values[row.key] || "")
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    readOnly: Boolean(row.modelData.readOnly)
                    onTextChanged: if (activeFocus) form.setValue(row.key, text)
                    padding: 12
                    background: Rectangle { radius: 10; color: uiTheme.current.colors.surface; border.color: multiline.activeFocus ? uiTheme.current.colors.primary : uiTheme.current.colors.fieldBorder; border.width: multiline.activeFocus ? 2 : 1 }
                }
            }
            RowLayout {
                visible: ["bool","choice","account","model","asr_model","multiline"].indexOf(row.kind) < 0
                Layout.fillWidth: true
                RoundedField {
                    objectName: "input_" + row.key
                    Accessible.name: row.modelData.label
                    Layout.fillWidth: true
                    readOnly: Boolean(row.modelData.readOnly)
                    text: form.values[row.key] === undefined ? "" : String(form.values[row.key])
                    selectByMouse: true
                    echoMode: row.kind === "secret" ? TextInput.Password : TextInput.Normal
                    inputMethodHints: row.kind === "secret" ? Qt.ImhSensitiveData | Qt.ImhNoPredictiveText : Qt.ImhNone
                    onTextEdited: form.setValue(row.key, text)
                }
                ActionButton {
                    Accessible.name: "选择" + row.modelData.label
                    text: "选择…"
                    symbol: row.kind === "color" ? "" : "folder-open"
                    display: row.kind === "color" ? AbstractButton.TextOnly : AbstractButton.IconOnly
                    ToolTip.text: "选择" + row.modelData.label
                    visible: ["folder","file","font","color"].indexOf(row.kind) >= 0
                    onClicked: {
                        form.pickerKey = row.key; form.pickerKind = row.kind
                        if (row.kind === "folder") directory.open()
                        else if (row.kind === "color") { colorDialog.selectedColor = form.values[row.key] || "#FFFFFF"; colorDialog.open() }
                        else { file.nameFilters = row.kind === "font" ? ["字体 (*.ttf *.otf *.ttc *.otc)"] : ["所有文件 (*)"]; file.open() }
                    }
                }
            }
        }
    }
    FolderDialog { id: directory; title: "选择保存目录"; onAccepted: form.setValue(form.pickerKey, bridge.filePath(selectedFolder.toString())) }
    FileDialog {
        id: file
        title: "选择文件"
        onAccepted: {
            const path = bridge.filePath(selectedFile.toString())
            if (form.pickerKind === "font") bridge.perform("importFont", {path:path})
            else form.setValue(form.pickerKey, path)
        }
    }
    ColorDialog { id: colorDialog; title: "选择颜色"; onAccepted: form.setValue(form.pickerKey, selectedColor.toString()) }
}
