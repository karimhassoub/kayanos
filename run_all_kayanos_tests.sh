#!/bin/bash
export PATH=$PATH:/home/karim/.local/bin

modules=(
"kayanos.kayanos_core.doctype.re_payment_plan_installment.test_re_payment_plan_installment"
"kayanos.kayanos_core.doctype.re_payment_schedule.test_re_payment_schedule"
"kayanos.kayanos_core.doctype.re_phase.test_re_phase"
"kayanos.kayanos_core.doctype.re_phase.test_re_phase3"
"kayanos.kayanos_core.doctype.re_phase_type.test_re_phase_type"
"kayanos.kayanos_core.doctype.re_project_profile.test_re_project_profile"
"kayanos.kayanos_core.doctype.re_property.test_re_property"
"kayanos.kayanos_core.doctype.re_property_type.test_re_property_type"
"kayanos.kayanos_core.doctype.re_reservation_settings.test_re_reservation_settings"
"kayanos.kayanos_core.doctype.re_sales_agreement.test_re_sales_agreement"
"kayanos.kayanos_core.doctype.re_unit.test_re_unit"
"kayanos.kayanos_core.doctype.re_unit_reservation.test_re_unit_reservation"
"kayanos.kayanos_core.doctype.re_unit_type.test_re_unit_type"
"kayanos.kayanos_core.test_billing_domain"
"kayanos.kayanos_core.test_customer_bridge"
"kayanos.kayanos_core.test_erpnext_billing"
"kayanos.kayanos_core.test_erpnext_bridge"
"kayanos.kayanos_core.test_erpnext_billing_cancellation"
)

for m in "${modules[@]}"; do
    echo "==================================="
    echo "Running Tests for: $m"
    echo "==================================="
    bench --site kayanos.localhost run-tests --module "$m" || echo "FAILED: $m"
done

echo "==================================="
echo "Running Tests for: kayanos.kayanos_core.test_erpnext_collections"
echo "==================================="
bench --site kayanos.localhost run-tests --module kayanos.kayanos_core.test_erpnext_collections

