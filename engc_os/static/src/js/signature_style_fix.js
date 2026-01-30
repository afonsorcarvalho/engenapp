/** @odoo-module **/

/**
 * Patch do componente NameAndSignature (core) para corrigir a aplicação do
 * estilo selecionado no dropdown "Estilo" na assinatura automática.
 *
 * Bug no core: onSelectFont(index) atribuía this.fonts[index] (dado da fonte)
 * a this.currentFont, mas drawCurrentName() usa this.fonts[this.currentFont],
 * esperando um índice numérico. Com isso, a pré-visualização principal não
 * atualizava para a fonte cursiva escolhida.
 *
 * Este patch mantém currentFont como índice, conforme esperado por drawCurrentName().
 */

import { patch } from "@web/core/utils/patch";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

patch(NameAndSignature.prototype, "EngcOsSignatureStyleFix", {
    /**
     * Atualiza a fonte selecionada pelo índice e redesenha a assinatura.
     * currentFont deve ser o índice em this.fonts; drawCurrentName() usa
     * this.fonts[this.currentFont].
     */
    onSelectFont(index) {
        this.currentFont = index;
        this.drawCurrentName();
    },
});
