/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Diálogo OWL que solicita únicamente la fecha de factura y la actualiza en el
 * servidor mediante RPC.
 *
 * Nota sobre `rpc.query`: era la API legacy de `web.rpc` (Odoo <= 16). En Odoo 17
 * fue eliminada; su equivalente es el servicio `rpc` (`useService("rpc")`), que
 * hace la misma llamada JSON-RPC a `/web/dataset/call_kw/<modelo>/<método>`.
 */
export class InvoiceDateDialog extends Component {
    static template = "patient_blood_type.InvoiceDateDialog";
    static components = { Dialog };
    static props = {
        moveId: { type: Number },
        invoiceDate: { type: [String, Boolean], optional: true },
        onSaved: { type: Function, optional: true },
        close: { type: Function },
    };

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.state = useState({
            invoiceDate: this.props.invoiceDate || "",
            saving: false,
        });
    }

    onDateInput(ev) {
        this.state.invoiceDate = ev.target.value;
    }

    async onSave() {
        if (!this.state.invoiceDate) {
            this.notification.add(_t("Debe indicar la fecha de factura."), { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            await this.rpc("/web/dataset/call_kw/account.move/action_update_invoice_date", {
                model: "account.move",
                method: "action_update_invoice_date",
                args: [[this.props.moveId], this.state.invoiceDate],
                kwargs: {},
            });
            this.notification.add(_t("Fecha de factura actualizada."), { type: "success" });
            this.props.close();
            if (this.props.onSaved) {
                await this.props.onSaved();
            }
        } finally {
            // Si el servidor rechaza el cambio (p. ej. factura validada), Odoo muestra
            // el error automáticamente y el diálogo queda abierto para corregir.
            this.state.saving = false;
        }
    }

    onCancel() {
        this.props.close();
    }
}

/**
 * Client action (función) invocada desde el botón "Editar fecha" de la factura:
 * abre el diálogo y, al guardar, recarga el formulario sin refrescar el navegador.
 */
function openInvoiceDateDialog(env, action) {
    const params = action.params || {};
    env.services.dialog.add(InvoiceDateDialog, {
        moveId: params.move_id,
        invoiceDate: params.invoice_date || false,
        onSaved: () => env.services.action.doAction({ type: "ir.actions.client", tag: "soft_reload" }),
    });
}

registry.category("actions").add("patient_blood_type.invoice_date_dialog", openInvoiceDateDialog);
