<script lang="ts">
	import { recordPayment } from '#lib/data/operations';
	import { db } from '#lib/data/store.svelte';
	import { customerById, invoiceBalance } from '#lib/data/selectors';
	import type { Invoice, PaymentMethod } from '#lib/data/types';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { formatDate, todayISO } from '#lib/utils/date';
	import { currency } from '#lib/utils/format';
	import Button from './ui/Button.svelte';
	import Icon from './ui/Icon.svelte';
	import Input from './ui/Input.svelte';
	import Modal from './ui/Modal.svelte';
	import Select from './ui/Select.svelte';
	import Textarea from './ui/Textarea.svelte';

	interface Props {
		open?: boolean;
		invoice?: Invoice | null;
		onclose: () => void;
		onrecorded?: () => void;
	}

	let { open = false, invoice = null, onclose, onrecorded }: Props = $props();

	let invoiceId = $state('');
	let amount = $state(0);
	let method = $state<PaymentMethod>('bank');
	let date = $state(todayISO());
	let note = $state('');
	let error = $state('');
	let saving = $state(false);

	const methodOptions = [
		{ value: 'bank', label: 'Bank transfer' },
		{ value: 'card', label: 'Card' },
		{ value: 'cash', label: 'Cash' },
		{ value: 'upi', label: 'UPI' }
	];

	let payable = $derived(
		db.data.invoices.filter((item) => item.status === 'confirmed' || item.status === 'draft')
	);

	let invoiceOptions = $derived(
		payable
			.map((item) => ({
				value: item.id,
				label: `${item.number} · ${customerById(db.data, item.customerId)?.company ?? 'Customer'} · ${currency(invoiceBalance(item))}`
			}))
			.sort((a, b) => a.label.localeCompare(b.label))
	);

	let selected = $derived(db.data.invoices.find((item) => item.id === invoiceId) ?? null);
	let balance = $derived(selected ? invoiceBalance(selected) : 0);

	$effect(() => {
		if (open) {
			invoiceId = invoice?.id ?? '';
			amount = invoice ? invoiceBalance(invoice) : 0;
			method = 'bank';
			date = todayISO();
			note = '';
			error = '';
		}
	});

	function pickInvoice() {
		const target = db.data.invoices.find((item) => item.id === invoiceId);
		amount = target ? invoiceBalance(target) : 0;
	}

	function submit() {
		error = '';
		if (!invoiceId) {
			error = 'Choose an invoice to pay.';
			return;
		}
		if (!Number.isFinite(amount) || amount <= 0) {
			error = 'Enter a payment amount greater than zero.';
			return;
		}
		if (balance > 0 && amount > balance + 0.001) {
			error = `The outstanding balance is ${currency(balance)}.`;
			return;
		}

		saving = true;
		const result = recordPayment({
			invoiceId,
			amount,
			method,
			date,
			note: note.trim()
		});
		saving = false;

		if (!result.ok) {
			error = result.error ?? 'Could not record the payment.';
			return;
		}

		toasts.success(`${currency(result.payment?.amount ?? amount)} payment recorded.`);
		onrecorded?.();
		onclose();
	}
</script>

<Modal
	{open}
	title="Record payment"
	description="Payments are applied to the selected invoice and update its status."
	{onclose}
>
	<form
		class="space-y-4"
		onsubmit={(event) => {
			event.preventDefault();
			submit();
		}}
	>
		{#if error}
			<p class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
				{error}
			</p>
		{/if}

		<Select
			label="Invoice"
			placeholder="Choose an invoice"
			bind:value={invoiceId}
			options={invoiceOptions}
			onchange={pickInvoice}
			required
		/>

		{#if selected}
			<div
				class="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500"
			>
				<span>Issued {formatDate(selected.issueDate)}</span>
				<span>Due {formatDate(selected.dueDate)}</span>
				<span class="ml-auto font-semibold text-slate-700">Balance {currency(balance)}</span>
			</div>
		{/if}

		<div class="grid gap-4 sm:grid-cols-2">
			<Input label="Amount" type="number" min={0} step="0.01" bind:value={amount} required />
			<Select label="Method" bind:value={method} options={methodOptions} />
			<Input label="Payment date" type="date" bind:value={date} required />
			{#if selected}
				<Button variant="outline" size="sm" class="self-end" onclick={() => (amount = balance)}>
					<Icon name="wallet" size={14} />
					Pay full balance
				</Button>
			{/if}
		</div>

		<Textarea
			label="Note"
			placeholder="Reference number or internal note"
			rows={2}
			bind:value={note}
		/>
	</form>

	{#snippet footer()}
		<Button variant="outline" onclick={onclose} disabled={saving}>Cancel</Button>
		<Button onclick={submit} disabled={saving}>
			{saving ? 'Recording…' : 'Record payment'}
		</Button>
	{/snippet}
</Modal>
