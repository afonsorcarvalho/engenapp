/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onWillUpdateProps, xml, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

/**
 * Componente customizado para exibir checklist agrupado por seções
 */
export class ChecklistGroupedWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            groupedItems: {},
            sections: [],
            loading: true,
            activeTab: null, // Controla qual aba está ativa
        });
        
        onWillStart(async () => {
            await this.loadChecklistData();
        });

        onWillUpdateProps(async (nextProps) => {
            // Compara os IDs do Many2many para detectar mudanças
            const getIds = (props) => {
                const fieldValue = props.value || props.record.data[props.name];
                if (!fieldValue) return [];
                
                if (fieldValue.currentIds && Array.isArray(fieldValue.currentIds)) {
                    return fieldValue.currentIds;
                }
                if (Array.isArray(fieldValue) && fieldValue.length > 0) {
                    if (Array.isArray(fieldValue[0]) && fieldValue[0][0] === 6 && fieldValue[0][2]) {
                        return fieldValue[0][2];
                    }
                    if (typeof fieldValue[0] === 'number') {
                        return fieldValue;
                    }
                    if (Array.isArray(fieldValue[0]) && fieldValue[0].length === 2) {
                        return fieldValue.map(item => item[0]);
                    }
                }
                return [];
            };
            
            const currentIds = getIds(this.props).sort();
            const nextIds = getIds(nextProps).sort();
            
            if (JSON.stringify(currentIds) !== JSON.stringify(nextIds)) {
                await this.loadChecklistData();
            }
        });
    }

    /**
     * Carrega os dados do checklist e agrupa por seção
     */
    async loadChecklistData() {
        const record = this.props.record;
        let checklistIds = [];
        
        // Tenta diferentes formas de acessar o campo Many2many
        const fieldValue = this.props.value || record.data[this.props.name];
        
        if (fieldValue) {
            // Se for um objeto com currentIds (formato do novo framework)
            if (fieldValue.currentIds && Array.isArray(fieldValue.currentIds)) {
                checklistIds = fieldValue.currentIds;
            }
            // Se for um array de IDs direto
            else if (Array.isArray(fieldValue) && fieldValue.length > 0) {
                // Se for comando Many2many [[6, False, [ids]]]
                if (Array.isArray(fieldValue[0]) && fieldValue[0][0] === 6 && fieldValue[0][2]) {
                    checklistIds = fieldValue[0][2];
                }
                // Se for array de IDs direto
                else if (typeof fieldValue[0] === 'number') {
                    checklistIds = fieldValue;
                }
                // Se for array de tuplas [id, name]
                else if (Array.isArray(fieldValue[0]) && fieldValue[0].length === 2) {
                    checklistIds = fieldValue.map(item => item[0]);
                }
            }
        }
        
        if (!checklistIds || checklistIds.length === 0) {
            this.state.loading = false;
            this.state.groupedItems = {};
            this.state.sections = [];
            return;
        }

        this.state.loading = true;

        try {
            // Busca os dados dos itens do checklist
            const checklistItems = await this.orm.read(
                "engc.os.verify.checklist",
                checklistIds,
                [
                    "id",
                    "sequence",
                    "section",
                    "instruction",
                    "check",
                    "tem_medicao",
                    "medicao",
                    "magnitude",
                    "observations",
                    "state",
                    "relatorio_id",
                ]
            );

            // Agrupa por seção
            const grouped = {};
            const sections = [];

            for (const item of checklistItems) {
                const sectionName = item.section ? item.section[1] : "Sem Seção";
                const sectionId = item.section ? item.section[0] : null;

                if (!grouped[sectionName]) {
                    grouped[sectionName] = {
                        id: sectionId,
                        name: sectionName,
                        items: [],
                    };
                    sections.push(sectionName);
                }

                grouped[sectionName].items.push({
                    ...item,
                    sectionName: sectionName,
                });
            }

            // Ordena os itens dentro de cada seção por sequence
            // E adiciona um índice sequencial para numeração
            for (const sectionName of sections) {
                grouped[sectionName].items.sort((a, b) => {
                    return (a.sequence || 0) - (b.sequence || 0);
                });
                // Adiciona índice sequencial para numeração
                grouped[sectionName].items.forEach((item, index) => {
                    item.sequentialNumber = index + 1;
                });
            }
            
            this.state.groupedItems = grouped;
            this.state.sections = sections;
            
            // Define a primeira seção como aba ativa se não houver uma ativa ou se a atual não existir mais
            if (sections.length > 0) {
                if (!this.state.activeTab || !sections.includes(this.state.activeTab)) {
                    this.state.activeTab = sections[0];
                }
            } else {
                this.state.activeTab = null;
            }
        } catch (error) {
            console.error("Erro ao carregar checklist:", error);
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Atualiza o estado de check de um item (atualização otimista)
     */
    async onCheckChange(item, event) {
        const checked = event.target.checked;
        
        // Atualização otimista: atualiza o estado local imediatamente
        item.check = checked;
        
        // Atualiza no backend de forma assíncrona sem recarregar tudo
        try {
            await this.orm.write("engc.os.verify.checklist", [item.id], {
                check: checked,
            });
        } catch (error) {
            console.error("Erro ao atualizar check:", error);
            // Reverte o estado local em caso de erro
            item.check = !checked;
            event.target.checked = !checked;
        }
    }

    /**
     * Atualiza a medição de um item (atualização otimista)
     */
    async onMedicaoChange(item, event) {
        const value = parseFloat(event.target.value) || 0;
        
        // Atualização otimista: atualiza o estado local imediatamente
        item.medicao = value;
        
        // Atualiza no backend de forma assíncrona
        try {
            await this.orm.write("engc.os.verify.checklist", [item.id], {
                medicao: value,
            });
        } catch (error) {
            console.error("Erro ao atualizar medição:", error);
            // Reverte o valor em caso de erro
            event.target.value = item.medicao || 0;
        }
    }

    /**
     * Atualiza as observações de um item (atualização otimista)
     */
    async onObservationsChange(item, event) {
        const value = event.target.value;
        
        // Atualização otimista: atualiza o estado local imediatamente
        item.observations = value;
        
        // Atualiza no backend de forma assíncrona
        try {
            await this.orm.write("engc.os.verify.checklist", [item.id], {
                observations: value,
            });
        } catch (error) {
            console.error("Erro ao atualizar observações:", error);
            // Reverte o valor em caso de erro
            event.target.value = item.observations || '';
        }
    }
    
    /**
     * Remove um item de checklist do relatório
     */
    async removeChecklistItem(item) {
        try {
            const record = this.props.record;
            const relatorioId = record.data.id;
            
            if (!relatorioId) {
                this.notification.add("⚠️ Erro: Relatório não encontrado.", {
                    type: "danger",
                    title: "Erro"
                });
                return;
            }
            
            // Abre dialog de confirmação do Odoo
            this.dialog.add(ConfirmationDialog, {
                title: "Confirmar Exclusão",
                body: `Tem certeza que deseja remover a instrução "${item.instruction}" do relatório?`,
                confirm: async () => {
                    try {
                        const fieldName = this.props.name || 'checklist_item_ids';
                        
                        // Atualização otimista: remove o item do estado local imediatamente
                        // Isso melhora a usabilidade, removendo o item da tela sem esperar o backend
                        const itemSection = item.sectionName || (item.section && item.section[1]) || (typeof item.section === 'string' ? item.section : null);
                        if (itemSection && this.state.groupedItems[itemSection] && this.state.groupedItems[itemSection].items) {
                            const items = this.state.groupedItems[itemSection].items;
                            const itemIndex = items.findIndex(i => i.id === item.id);
                            if (itemIndex !== -1) {
                                items.splice(itemIndex, 1);
                                
                                // Se não há mais itens na seção, remove a seção
                                if (items.length === 0) {
                                    delete this.state.groupedItems[itemSection];
                                    const sectionIndex = this.state.sections.indexOf(itemSection);
                                    if (sectionIndex !== -1) {
                                        this.state.sections.splice(sectionIndex, 1);
                                    }
                                    // Se a aba ativa foi removida, ativa a primeira disponível
                                    if (this.state.activeTab === itemSection && this.state.sections.length > 0) {
                                        this.state.activeTab = this.state.sections[0];
                                    }
                                } else {
                                    // Recalcula os números sequenciais
                                    items.forEach((it, idx) => {
                                        it.sequentialNumber = idx + 1;
                                    });
                                }
                            }
                        }
                        
                        // Força renderização imediata
                        this.render();
                        
                        // Atualiza o campo Many2many localmente removendo o ID
                        const fieldValue = this.props.value || record.data[fieldName];
                        if (fieldValue && fieldValue.currentIds) {
                            const currentIds = fieldValue.currentIds.filter(id => id !== item.id);
                            if (fieldValue.replaceWith) {
                                await fieldValue.replaceWith(currentIds);
                            } else if (fieldValue.setCurrentIds) {
                                fieldValue.setCurrentIds(currentIds);
                            }
                        }
                        
                        // Chama o método do backend para remover o item (em background)
                        this.orm.call(
                            "engc.os.relatorios",
                            "action_remove_checklist_item",
                            [[relatorioId], item.id]
                        ).then(async () => {
                            // Após sucesso no backend, sincroniza os dados
                            try {
                                // Força atualização do campo Many2many lendo novamente do servidor
                                if (record && record.model && record.model.resModel) {
                                    const updatedRecord = await this.orm.read(
                                        record.model.resModel,
                                        [record.resId],
                                        [fieldName]
                                    );
                                    if (updatedRecord && updatedRecord[0] && updatedRecord[0][fieldName]) {
                                        const newIds = updatedRecord[0][fieldName];
                                        if (Array.isArray(newIds)) {
                                            const fieldValue = this.props.value || record.data[fieldName];
                                            if (fieldValue && fieldValue.replaceWith) {
                                                await fieldValue.replaceWith(newIds);
                                            }
                                        }
                                    }
                                }
                                
                                // Recarrega o record para sincronizar
                                if (record && record.model) {
                                    await record.model.load({
                                        resId: record.resId,
                                    });
                                    if (record.__syncData) {
                                        record.__syncData();
                                    }
                                    if (record.model.notify) {
                                        record.model.notify();
                                    }
                                }
                                
                                // Recarrega os dados do checklist para garantir sincronização
                                await this.loadChecklistData();
                                this.render();
                            } catch (syncError) {
                                console.warn("Erro ao sincronizar após remoção:", syncError);
                            }
                        }).catch((error) => {
                            // Em caso de erro, recarrega os dados para reverter
                            console.error("Erro ao remover item do checklist:", error);
                            this.loadChecklistData().then(() => this.render());
                            
                            let errorMessage = "Erro desconhecido";
                            if (error && typeof error === 'object') {
                                if (error.data && error.data.message) {
                                    errorMessage = error.data.message;
                                } else if (error.message) {
                                    errorMessage = error.message;
                                } else {
                                    errorMessage = String(error);
                                }
                            } else if (error) {
                                errorMessage = String(error);
                            }
                            
                            this.notification.add(`Erro ao remover instrução: ${errorMessage}`, {
                                type: "danger",
                                title: "Erro"
                            });
                        });
                        
                        // Mostra toast de sucesso imediatamente
                        this.notification.add(`Instrução "${item.instruction}" removida com sucesso.`, {
                            type: "success",
                            title: "Sucesso"
                        });
                    } catch (error) {
                        console.error("Erro ao remover item do checklist:", error);
                        let errorMessage = "Erro desconhecido";
                        
                        if (error && typeof error === 'object') {
                            if (error.data && error.data.message) {
                                errorMessage = error.data.message;
                            } else if (error.message) {
                                errorMessage = error.message;
                            } else {
                                errorMessage = String(error);
                            }
                        } else if (error) {
                            errorMessage = String(error);
                        }
                        
                        this.notification.add(`Erro ao remover instrução: ${errorMessage}`, {
                            type: "danger",
                            title: "Erro"
                        });
                    }
                },
                confirmLabel: "Remover",
                cancelLabel: "Cancelar",
            });
        } catch (error) {
            console.error("Erro ao abrir dialog de confirmação:", error);
            this.notification.add("Erro ao abrir confirmação de exclusão.", {
                type: "danger",
                title: "Erro"
            });
        }
    }
    
    /**
     * Abre a view de seleção para adicionar instruções do checklist
     */
    async loadInstructions() {
        try {
            const record = this.props.record;
            const relatorioId = record.data.id;
            
            if (!relatorioId) {
                this.notification.add("⚠️ Por favor, salve o relatório antes de adicionar instruções.", {
                    type: "warning",
                    title: "Atenção"
                });
                return;
            }
            
            // Chama o método do modelo que retorna a ação para abrir a view de seleção
            const action = await this.orm.call(
                "engc.os.relatorios",
                "action_open_checklist_selection",
                [[relatorioId]]
            );
            
            // Valida se a ação foi retornada corretamente
            if (!action || typeof action !== 'object') {
                throw new Error("Ação inválida retornada pelo servidor");
            }
            
            // Executa a ação para abrir a view de seleção
            // O Odoo automaticamente adiciona os itens selecionados ao campo Many2many
            // quando a view é fechada, devido ao contexto active_field e active_model
            this.action.doAction(action, {
                onClose: async (closeInfo) => {
                    // Quando a view de seleção for fechada, recarrega os dados
                    // Aguarda um pouco para garantir que o Odoo processou a seleção
                    setTimeout(async () => {
                        try {
                            const fieldName = this.props.name || 'checklist_item_ids';
                            
                            // Força atualização do campo Many2many lendo novamente do servidor
                            // Isso garante que temos os dados mais recentes
                            if (record && record.model && record.model.resModel) {
                                try {
                                    const updatedRecord = await this.orm.read(
                                        record.model.resModel,
                                        [record.resId],
                                        [fieldName]
                                    );
                                    if (updatedRecord && updatedRecord[0] && updatedRecord[0][fieldName]) {
                                        // Atualiza o campo no record
                                        const newIds = updatedRecord[0][fieldName];
                                        if (Array.isArray(newIds)) {
                                            // Atualiza os IDs do campo Many2many usando replaceWith
                                            const fieldValue = this.props.value || record.data[fieldName];
                                            if (fieldValue) {
                                                if (fieldValue.replaceWith) {
                                                    await fieldValue.replaceWith(newIds);
                                                } else if (fieldValue.setCurrentIds) {
                                                    fieldValue.setCurrentIds(newIds);
                                                } else if (fieldValue.load) {
                                                    await fieldValue.load();
                                                }
                                            }
                                        }
                                    }
                                } catch (readError) {
                                    console.warn("Erro ao ler campo atualizado:", readError);
                                }
                            }
                            
                            // Recarrega o record completo para atualizar o campo Many2many
                            if (record && record.model) {
                                // Recarrega o record do modelo
                                await record.model.load({
                                    resId: record.resId,
                                });
                                
                                // Sincroniza os dados do record
                                if (record.__syncData) {
                                    record.__syncData();
                                }
                                // Notifica o modelo para atualizar a view
                                if (record.model.notify) {
                                    record.model.notify();
                                }
                            } else if (record && typeof record.load === 'function') {
                                await record.load();
                            }
                            
                            // Aguarda um pouco mais para garantir que os dados foram atualizados
                            await new Promise(resolve => setTimeout(resolve, 200));
                            
                            // Recarrega os dados do checklist no widget
                            await this.loadChecklistData();
                            
                            // Força renderização do componente
                            this.render();
                        } catch (reloadError) {
                            console.error("Erro ao recarregar dados após fechar seleção:", reloadError);
                        }
                    }, 500);
                },
            }).catch((doActionError) => {
                // Se doAction falhar, mostra o erro
                console.error("Erro ao executar doAction:", doActionError);
                throw doActionError;
            });
        } catch (error) {
            console.error("Erro ao abrir seleção de instruções:", error);
            let errorMessage = "Erro desconhecido";
            
            if (error && typeof error === 'object') {
                if (error.data && error.data.message) {
                    errorMessage = error.data.message;
                } else if (error.message) {
                    errorMessage = error.message;
                } else {
                    errorMessage = String(error);
                }
            } else if (error) {
                errorMessage = String(error);
            }
            
            this.notification.add(`Erro ao abrir seleção de instruções: ${errorMessage}`, {
                type: "danger",
                title: "Erro"
            });
        }
    }

    /**
     * Verifica se o campo está readonly
     */
    get isReadonly() {
        if (this.props.readonly) {
            return true;
        }
        const state = this.props.record.data.state;
        return state && state !== "draft";
    }
    
    /**
     * Ativa uma aba específica
     */
    activateTab(sectionName) {
        this.state.activeTab = sectionName;
    }
}

ChecklistGroupedWidget.template = xml`
    <div class="checklist-grouped-widget o_field_widget">
        <div t-if="state.loading" class="text-center p-3">
            <i class="fa fa-spinner fa-spin"/> Carregando checklist...
        </div>
        
        <div t-if="!state.loading and state.sections.length === 0" class="alert alert-info" style="width: 100%;">
            <i class="fa fa-info-circle"/> Nenhum item de checklist encontrado.
            <div class="mt-2" t-if="!isReadonly">
                <button 
                    type="button"
                    class="btn btn-primary btn-sm"
                    t-on-click="() => this.loadInstructions()">
                    <i class="fa fa-plus me-2"/>
                    Carregar Instruções do Plano de Manutenção
                </button>
            </div>
        </div>
        
        <div t-if="!state.loading and state.sections.length > 0" class="checklist-sections" style="width: 100%;">
            <!-- Botão para carregar instruções -->
            <div class="mb-3 text-end" t-if="!isReadonly" style="width: 100%;">
                <button 
                    type="button"
                    class="btn btn-primary"
                    t-on-click="() => this.loadInstructions()">
                    <i class="fa fa-plus me-2"/>
                    Adicionar Instruções
                </button>
            </div>
            
            <!-- Navegação por Abas -->
            <ul class="nav nav-tabs mb-3" role="tablist" style="width: 100%;">
                <li t-foreach="state.sections" t-as="sectionName" t-key="sectionName" class="nav-item" role="presentation">
                    <a 
                        class="nav-link" 
                        t-attf-class="{{ sectionName === state.activeTab ? 'active' : '' }}"
                        t-on-click.prevent="() => this.activateTab(sectionName)"
                        href="#"
                        role="tab"
                        tabindex="0">
                        <i class="fa fa-folder-open me-2"/>
                        <t t-esc="sectionName"/>
                        <span class="badge badge-secondary ms-2">
                            <t t-esc="state.groupedItems[sectionName].items.length"/>
                        </span>
                    </a>
                </li>
            </ul>
            
            <!-- Conteúdo das Abas -->
            <div class="tab-content" style="width: 100%;">
                <div t-foreach="state.sections" t-as="sectionName" t-key="sectionName" 
                     class="tab-pane" 
                     t-attf-class="{{ sectionName === state.activeTab ? 'active' : '' }}">
                    <div class="table-responsive" style="width: 100%;">
                        <table class="o_list_table table table-sm table-hover table-striped mb-0" style="width: 100%; table-layout: fixed;">
                            <thead>
                                <tr>
                                    <th style="width: 4%; min-width: 40px;" class="text-center">#</th>
                                    <th style="width: auto; min-width: 200px;">Instrução</th>
                                    <th style="width: 6%; min-width: 60px;" class="text-center">Check</th>
                                    <th style="width: 12%; min-width: 100px;" class="text-center">Medição</th>
                                    <th style="width: 10%; min-width: 80px;" class="text-center">Grandeza</th>
                                    <th style="width: 20%; min-width: 150px;">Observações</th>
                                    <th style="width: 5%; min-width: 50px;" class="text-center" t-if="!isReadonly">Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr t-foreach="state.groupedItems[sectionName].items" t-as="item" t-key="item.id">
                                    <td class="text-center o_list_number">
                                        <t t-esc="item.sequentialNumber"/>
                                    </td>
                                    <td class="o_list_text">
                                        <t t-esc="item.instruction"/>
                                    </td>
                                    <td class="text-center">
                                        <div class="o_field_boolean o_field_widget">
                                            <input 
                                                type="checkbox" 
                                                t-att-checked="item.check"
                                                t-att-disabled="isReadonly"
                                                t-on-change="(ev) => this.onCheckChange(item, ev)"/>
                                        </div>
                                    </td>
                                    <td class="text-center">
                                        <t t-if="item.tem_medicao">
                                            <div class="o_field_float o_field_widget o_input">
                                                <input 
                                                    type="number" 
                                                    step="0.01"
                                                    t-att-value="item.medicao || 0"
                                                    t-att-disabled="isReadonly"
                                                    t-on-change="(ev) => this.onMedicaoChange(item, ev)"
                                                    class="o_input checklist-input-no-border"
                                                    style="width: 100px; text-align: right;"/>
                                            </div>
                                        </t>
                                        <span t-if="!item.tem_medicao" class="text-muted">-</span>
                                    </td>
                                    <td class="text-center">
                                        <t t-if="item.tem_medicao and item.magnitude">
                                            <span class="badge badge-info">
                                                <t t-esc="item.magnitude"/>
                                            </span>
                                        </t>
                                        <span t-if="!item.tem_medicao or !item.magnitude" class="text-muted">-</span>
                                    </td>
                                    <td style="width: 20%; min-width: 150px;">
                                        <div class="o_field_char o_field_widget o_input" style="width: 100%;">
                                            <input 
                                                type="text" 
                                                t-att-value="item.observations || ''"
                                                t-att-disabled="isReadonly"
                                                t-on-change="(ev) => this.onObservationsChange(item, ev)"
                                                class="o_input checklist-input-no-border"
                                                style="width: 100%;"
                                                placeholder="Observações..."/>
                                        </div>
                                    </td>
                                    <td t-if="!isReadonly" class="text-center" style="width: 5%; min-width: 50px;">
                                        <button 
                                            type="button"
                                            class="btn btn-sm btn-danger"
                                            t-on-click="() => this.removeChecklistItem(item)"
                                            title="Remover instrução">
                                            <i class="fa fa-trash"/>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
`;

ChecklistGroupedWidget.props = {
    ...standardFieldProps,
};

// Registra o widget
registry.category("fields").add("checklist_grouped", ChecklistGroupedWidget);
