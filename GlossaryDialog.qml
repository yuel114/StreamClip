import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

AppDialog {
    id:dialog
    objectName:"glossaryDialog"
    title:"术语与候选"
    modal:true
    closePolicy:Popup.NoAutoClose
    property string scope:""
    property string candidateStatus:"pending"
    property var termIds:[]
    property var candidateIds:[]
    property string noteBaseline:""
    property var discardAction:null
    property int sourceRecording:0
    function hasUnsaved() { return opened && (termForm.dirty || candidateForm.dirty || note.text!==noteBaseline) }
    function guard(action) { if (hasUnsaved()) { discardAction=action; discard.open() } else action() }
    function requestClose() { if(bridge.busy)return;guard(function(){termForm.dirty=false;candidateForm.dirty=false;noteBaseline=note.text;dialog.close()}) }
    function selectScope(value) {
        guard(function(){scope=value;termIds=[];candidateIds=[];termForm.reset({enabled:true});candidateForm.reset({});noteBaseline="";note.text="";bridge.setGlossary(scope,candidateStatus,true)})
    }
    function scopeIndex() { for(let i=0;i<scopeCombo.model.length;i++)if(scopeCombo.model[i].value===dialog.scope)return i;return 0 }
    function toggleId(values,id,enabled) { return enabled ? values.filter(v=>v!==id).concat([id]) : values.filter(v=>v!==id) }
    function discardEdits() {
        termForm.reset(bridge.glossary.entries.find(e=>e.id===termForm.values.id)||{enabled:true})
        candidateForm.reset(bridge.glossary.candidates.find(e=>e.id===candidateForm.values.id)||{})
        noteBaseline=bridge.glossary.note;note.text=noteBaseline
    }
    function editTerm(data) { guard(function(){termIds=[data.id];termForm.reset(data)}) }
    function editCandidate(data) { guard(function(){candidateIds=[data.id];candidateForm.reset(data)}) }
    function perform(action, values) { bridge.perform(action,Object.assign({scope:scope},values)) }
    onAboutToShow:bridge.setGlossary(scope,candidateStatus,true)
    onClosed:bridge.setGlossary(scope,candidateStatus,false)
    Shortcut { sequence:"Escape"; enabled:dialog.opened; onActivated:dialog.requestClose() }
    Connections {
        target:bridge
        function onGlossaryChanged() {
            if(bridge.glossary.scope!==dialog.scope)return
            if(note.text===dialog.noteBaseline) { dialog.noteBaseline=bridge.glossary.note; note.text=dialog.noteBaseline }
            if(!dialog.sourceRecording&&bridge.glossary.recordings.length)dialog.sourceRecording=bridge.glossary.recordings[0].id
        }
        function onActionDone(action,data) {
            if(action==="glossaryKnowledge"&&data.scope===dialog.scope)note.text=data.note
            if(action==="glossaryTerm"&&data.entry.channel_id===dialog.scope){termForm.reset(data.entry);dialog.termIds=[data.entry.id]}
            if(action==="glossaryNote")dialog.noteBaseline=note.text
            if(action==="glossaryApprove"||action==="glossaryReject") { candidateForm.reset({});dialog.candidateIds=[] }
            if(action==="glossaryChange") { termForm.reset({enabled:true});dialog.termIds=[] }
        }
    }
    ColumnLayout {
        anchors.fill:parent; spacing:10
        enabled: !bridge.busy
        RowLayout {
            Label { textFormat: Text.PlainText; text:"选择主播" }
            ChoiceBox {
                id:scopeCombo; objectName:"glossaryScope"; Layout.fillWidth:true; textRole:"label"; valueRole:"value"
                model:[{value:"",label:"全局术语"}].concat(bridge.glossary.channels.map(c=>({value:c.channel_id,label:c.name+(c.room_id?" · 直播间 "+c.room_id:" · UID "+c.channel_id)})))
                currentIndex:dialog.scopeIndex()
                onActivated:{ const value=currentValue;dialog.selectScope(value);currentIndex=Qt.binding(dialog.scopeIndex) }
            }
            Label { textFormat: Text.PlainText; text:"主播资料在“直播间”页维护"; color:uiTheme.current.colors.muted }
        }
        SegmentedBar {
            id:tabs; objectName:"glossaryTabs"; Layout.fillWidth:true
            PageTab { text:"术语表" }
            PageTab { text:"主播知识库" }
            PageTab { text:"候选审核" }
        }
        StackLayout {
            Layout.fillWidth:true; Layout.fillHeight:true; currentIndex:tabs.currentIndex
            ColumnLayout {
                RowLayout {
                    RoundedField { id:search; placeholderText:"搜索原始写法、规范写法或分类"; Accessible.name:placeholderText; Layout.fillWidth:true; selectByMouse:true }
                    ActionButton { text:"新建词条"; onClicked:dialog.guard(function(){dialog.termIds=[];termForm.reset({enabled:true})}) }
                    ActionButton { text:"导入"; onClicked:openFile.open() }
                    ActionButton { text:"导出"; onClicked:saveFile.open() }
                }
                SplitView {
                    Layout.fillWidth:true; Layout.fillHeight:true
                    ListView {
                        id:terms; objectName:"glossaryTerms"; SplitView.fillWidth:true; SplitView.minimumWidth:270; clip:true; reuseItems:true
                        model:bridge.glossary.entries.filter(e=>!search.text||(e.term+e.canonical+e.category).toLowerCase().indexOf(search.text.toLowerCase())>=0)
                        ScrollBar.vertical:ScrollBar {}
                        delegate:ListEntry {
                            required property var modelData
                            width:ListView.view.width; height:70; highlighted:dialog.termIds.indexOf(modelData.id)>=0
                            onClicked:dialog.editTerm(modelData)
                            contentItem:RowLayout {
                                CheckBox { checked:dialog.termIds.indexOf(modelData.id)>=0; onToggled:dialog.termIds=dialog.toggleId(dialog.termIds,modelData.id,checked) }
                                ColumnLayout {
                                    Layout.fillWidth:true
                                    Label { textFormat: Text.PlainText; text:modelData.term+" → "+modelData.canonical; Layout.fillWidth:true; elide:Text.ElideRight }
                                    Label { textFormat: Text.PlainText; text:(modelData.channel_id?"主播":"全局")+" · "+(modelData.enabled?"启用":"停用")+" · "+modelData.category; color:uiTheme.current.colors.muted }
                                }
                            }
                        }
                        Label { textFormat: Text.PlainText; anchors.centerIn:parent; text:"暂无匹配词条"; visible:terms.count===0; color:uiTheme.current.colors.muted }
                    }
                    ScrollView {
                        SplitView.preferredWidth:280; SplitView.minimumWidth:240; contentWidth:availableWidth; clip:true
                        ColumnLayout {
                            width:parent.width
                            FormFields { id:termForm; objectName:"termEditor"; Layout.fillWidth:true; values:({enabled:true}); fields:[{key:"term",label:"原始写法",kind:"text"},{key:"canonical",label:"规范写法",kind:"text"},{key:"category",label:"分类",kind:"text"},{key:"enabled",label:"启用词条",kind:"bool"}] }
                            ActionButton { text:"保存词条"; primary:true; enabled:!bridge.busy; onClicked:dialog.perform("glossaryTerm",termForm.values) }
                        }
                    }
                }
                RowLayout {
                    ActionButton { text:"启用选中"; enabled:dialog.termIds.length>0&&!bridge.busy; onClicked:dialog.guard(function(){dialog.perform("glossaryChange",{ids:dialog.termIds,operation:"enable"})}) }
                    ActionButton { text:"停用选中"; enabled:dialog.termIds.length>0&&!bridge.busy; onClicked:dialog.guard(function(){dialog.perform("glossaryChange",{ids:dialog.termIds,operation:"disable"})}) }
                    ActionButton { text:"删除选中"; enabled:dialog.termIds.length>0&&!bridge.busy; onClicked:deleteDialog.open() }
                    Label { textFormat: Text.PlainText; text:"主播同名词条覆盖全局；停用项会屏蔽全局词条。"; color:uiTheme.current.colors.muted; wrapMode:Text.Wrap; Layout.fillWidth:true }
                }
            }
            ColumnLayout {
                Label { textFormat: Text.PlainText; text:"只读取对应主播的萌娘百科词条正文，由 AI 总结。再次填写会重新生成摘要，手工补充保留；检查后保存。仅需配置 AI 模型，无需搜索 Key。"; color:uiTheme.current.colors.muted; wrapMode:Text.Wrap; Layout.fillWidth:true }
                ScrollView { Layout.fillWidth:true; Layout.fillHeight:true; contentWidth:availableWidth; TextArea { id:note; objectName:"knowledgeEditor"; textFormat:TextEdit.PlainText; wrapMode:TextEdit.Wrap; selectByMouse:true; placeholderText:"点击一键填写，读取主播的萌娘百科词条并生成简明摘要。\n\n也可在此记录手工补充。" } }
                RowLayout {
                    ActionButton { objectName:"fillKnowledge"; text:bridge.busy?"正在处理…":"主播知识库一键填写"; enabled:dialog.scope.length>0&&!bridge.busy; onClicked:dialog.perform("glossaryKnowledge",{note:note.text}) }
                    ActionButton { text:"保存知识库"; primary:true; enabled:!bridge.busy; onClicked:dialog.perform("glossaryNote",{note:note.text}) }
                    Item { Layout.fillWidth:true }
                }
            }
            ColumnLayout {
                RowLayout {
                    ChoiceBox {
                        textRole:"label"; valueRole:"value"
                        model:[{label:"待审核",value:"pending"},{label:"已通过",value:"approved"},{label:"已拒绝",value:"rejected"}]
                        currentIndex:["pending","approved","rejected"].indexOf(dialog.candidateStatus)
                        onActivated:{const value=currentValue;dialog.guard(function(){dialog.candidateStatus=value;dialog.candidateIds=[];candidateForm.reset({});bridge.setGlossary(dialog.scope,dialog.candidateStatus,true)});currentIndex=Qt.binding(function(){return ["pending","approved","rejected"].indexOf(dialog.candidateStatus)})}
                    }
                    ChoiceBox {
                        Layout.fillWidth:true; textRole:"label"; valueRole:"value"
                        model:bridge.glossary.recordings.map(r=>({value:r.id,label:"#"+r.id+" · "+r.title}))
                        currentIndex:indexOfValue(dialog.sourceRecording)
                        onActivated:dialog.sourceRecording=currentValue
                    }
                    ActionButton { text:"发现新术语"; enabled:dialog.scope.length>0&&dialog.sourceRecording>0&&!bridge.busy; onClicked:dialog.perform("glossaryJob",{mode:"discover",recording_id:dialog.sourceRecording}) }
                    ActionButton { text:"AI 复核待审"; enabled:dialog.scope.length>0&&!bridge.busy; onClicked:dialog.perform("glossaryJob",{mode:"review"}) }
                }
                SplitView {
                    Layout.fillWidth:true; Layout.fillHeight:true
                    ListView {
                        id:candidates; SplitView.fillWidth:true; SplitView.minimumWidth:270; clip:true; model:bridge.glossary.candidates; reuseItems:true
                        ScrollBar.vertical:ScrollBar {}
                        delegate:ListEntry {
                            required property var modelData
                            width:ListView.view.width; height:80; highlighted:dialog.candidateIds.indexOf(modelData.id)>=0
                            onClicked:dialog.editCandidate(modelData)
                            contentItem:RowLayout {
                                CheckBox { checked:dialog.candidateIds.indexOf(modelData.id)>=0; onToggled:dialog.candidateIds=dialog.toggleId(dialog.candidateIds,modelData.id,checked) }
                                ColumnLayout {
                                    Layout.fillWidth:true
                                    Label { textFormat: Text.PlainText; text:modelData.term+" → "+modelData.canonical; Layout.fillWidth:true; elide:Text.ElideRight }
                                    Label { textFormat: Text.PlainText; text:modelData.category+" · 置信度 "+Number(modelData.confidence).toFixed(2); color:uiTheme.current.colors.muted }
                                    Label { textFormat: Text.PlainText; text:"来源 #"+modelData.first_session_id+" → #"+modelData.last_session_id; color:uiTheme.current.colors.muted; font.pixelSize:12 }
                                }
                            }
                        }
                        Label { textFormat: Text.PlainText; anchors.centerIn:parent; text:"暂无候选"; visible:candidates.count===0; color:uiTheme.current.colors.muted }
                    }
                    ScrollView {
                        SplitView.preferredWidth:300; SplitView.minimumWidth:240; contentWidth:availableWidth; clip:true
                        ColumnLayout {
                            width:parent.width
                            FormFields { id:candidateForm; Layout.fillWidth:true; fields:[{key:"term",label:"原始写法",kind:"text"},{key:"canonical",label:"通过前修正写法",kind:"text"},{key:"category",label:"分类",kind:"text"}] }
                            TextArea { text:(candidateForm.values.id?"综合分 "+Number(candidateForm.values.score*100).toFixed(0)+"% · 约 "+candidateForm.values.occurrence_count+" 次 · "+candidateForm.values.session_count+" 场\n\n":"")+"候选依据："+(candidateForm.values.reason||"")+"\n\nAI 复核："+(candidateForm.values.ai_review||"尚未复核"); readOnly:true; selectByMouse:true; wrapMode:TextEdit.Wrap; Layout.fillWidth:true; background:null }
                        }
                    }
                }
                RowLayout {
                    ActionButton { text:"通过选中"; primary:true; enabled:dialog.candidateIds.length>0&&!bridge.busy; onClicked:dialog.perform("glossaryApprove",{ids:dialog.candidateIds,edit:dialog.candidateIds.length===1&&candidateForm.values.id===dialog.candidateIds[0]?candidateForm.values:null}) }
                    ActionButton { text:"拒绝选中"; enabled:dialog.candidateIds.length>0&&!bridge.busy; onClicked:dialog.perform("glossaryReject",{ids:dialog.candidateIds}) }
                    Label { textFormat: Text.PlainText; text:"AI 复核不会自动通过；批量通过使用各条建议写法。"; color:uiTheme.current.colors.muted; wrapMode:Text.Wrap; Layout.fillWidth:true }
                }
                ActionButton { text:dialog.scope?"将所选录播关联到当前主播":"将所选录播恢复自动匹配"; enabled:dialog.sourceRecording>0&&!bridge.busy; onClicked:dialog.perform("glossaryBind",{recording_id:dialog.sourceRecording}) }
            }
        }
        RowLayout {
            Label { textFormat: Text.PlainText; text:bridge.status; color:uiTheme.current.colors.muted; Layout.fillWidth:true; elide:Text.ElideRight }
            ActionButton { text:"关闭"; onClicked:dialog.requestClose() }
        }
    }
    AppDialog { id:discard; objectName:"glossaryDiscard"; title:"尚未保存"; anchors.centerIn:parent; width:380; modal:true; standardButtons:Dialog.Yes|Dialog.No; onOpened:{standardButton(Dialog.Yes).text="放弃修改";standardButton(Dialog.No).text="继续编辑"} onAccepted:{dialog.discardEdits();if(dialog.discardAction)dialog.discardAction()} Label { textFormat: Text.PlainText; text:"放弃当前未保存的词条、候选或备注修改？"; width:parent.width; wrapMode:Text.Wrap } }
    AppDialog { id:deleteDialog; title:"删除词条"; destructive:true; anchors.centerIn:parent; width:360; modal:true; standardButtons:Dialog.Yes|Dialog.No; onOpened:{standardButton(Dialog.Yes).text="删除";standardButton(Dialog.No).text="取消"} onAccepted:dialog.perform("glossaryChange",{ids:dialog.termIds,operation:"delete"}); Label { textFormat: Text.PlainText; text:"删除选中的 "+dialog.termIds.length+" 条词条？" } }
    FileDialog { id:openFile; title:"导入术语表"; nameFilters:["术语表 (*.json *.md *.markdown)"]; onAccepted:dialog.perform("glossaryImport",{path:selectedFile.toString()}) }
    FileDialog { id:saveFile; title:"导出术语表"; fileMode:FileDialog.SaveFile; defaultSuffix:"json"; nameFilters:["JSON (*.json)"]; onAccepted:dialog.perform("glossaryExport",{path:selectedFile.toString()}) }
}
