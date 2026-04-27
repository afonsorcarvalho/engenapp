/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useRef, useEffect, onMounted } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useInputField } from "@web/views/fields/input_field_hook";

export class AceEditorField extends owl.Component {
    static template = "afr_supervisorio_ciclos.AceEditor";
    static props = standardFieldProps;

    setup() {
        this.editorRef = useRef("ace-editor");
        this.editor = null;
        
        useInputField({
            getValue: () => this.props.value,
            refName: "ace-editor",
        });
        useEffect(() => {
            if (this.editor && this.props.value !== this.editor.getValue()) {
                this.editor.setValue(this.props.value || "", -1);
            }
        }, () => [this.props.value]);
        onMounted(() => {
            this._loadAceEditor();
        });
    }

    _loadAceEditor() {
        if (!window.ace) {
            const script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.js';
            script.async = true;
            
            script.onload = () => {
                this._initializeEditor();
            };
            
            document.head.appendChild(script);
        } else {
            this._initializeEditor();
        }
    }

    _initializeEditor() {
        if (!this.editorRef.el) return;
        
        this.editor = ace.edit(this.editorRef.el);
        
        const options = this.props.record.activeFields[this.props.name].options || {};
        
        this.editor.setTheme("ace/theme/" + (options.theme || "monokai"));
        this.editor.getSession().setMode("ace/mode/" + (options.mode || "text"));
        
        this.editor.setOptions({
            fontSize: options.fontSize || 14,
           
            showPrintMargin: options.showPrintMargin || false,
            showGutter: options.showGutter || true,
            maxLines: options.maxLines || 30,
            minLines: options.minLines || 10,
            behavioursEnabled: options.behavioursEnabled !== undefined ? options.behavioursEnabled : false,
            wrapBehavioursEnabled: options.wrapBehavioursEnabled !== undefined ? options.wrapBehavioursEnabled : false,
        });
        
        this.editor.setValue(this.props.value || "", -1);
        this.editor.setReadOnly(this.props.readonly || false);
        
        this.editor.on("change", () => {
            this.props.update(this.editor.getValue());
        });
    }
}

registry.category("fields").add("ace_editor", AceEditorField);