<script lang="ts">
	import type { Invoice } from '#lib/data/types';
	import { customerById, invoiceBalance, invoiceState, taxRate } from '#lib/data/selectors';
	import { db } from '#lib/data/store.svelte';
	import { formatDate } from '#lib/utils/date';
	import { currency } from '#lib/utils/format';
	import BrandMark from './BrandMark.svelte';
	import StatusBadge from './ui/StatusBadge.svelte';

	interface Props {
		invoice: Invoice;
	}

	let { invoice }: Props = $props();

	let customer = $derived(customerById(db.data, invoice.customerId));
	let subscription = $derived(
		db.data.subscriptions.find((item) => item.id === invoice.subscriptionId) ?? null
	);
	let balance = $derived(invoiceBalance(invoice));
</script>

<article
	class="print-area rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-900/[0.03] sm:p-9"
>
	<div class="flex flex-wrap items-start justify-between gap-6">
		<div>
			<BrandMark href="/dashboard" class="pointer-events-none" />
			<p class="mt-4 text-xs leading-relaxed text-slate-500">
				Brightloop Billing OS<br />
				1 Market Plaza, Suite 500<br />
				San Francisco, CA 94105
			</p>
		</div>
		<div class="text-right">
			<p class="text-[11px] font-semibold tracking-[0.25em] text-slate-400 uppercase">Invoice</p>
			<p class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{invoice.number}</p>
			<div class="mt-2 flex justify-end">
				<StatusBadge status={invoiceState(invoice)} />
			</div>
		</div>
	</div>

	<div class="mt-8 grid gap-6 border-t border-slate-100 pt-6 sm:grid-cols-3">
		<div>
			<p class="text-[11px] font-semibold tracking-wide text-slate-400 uppercase">Billed to</p>
			<p class="mt-2 text-sm font-semibold text-slate-900">{customer?.company ?? 'Customer'}</p>
			<p class="text-xs text-slate-500">{customer?.name ?? ''}</p>
			<p class="mt-1 text-xs leading-relaxed text-slate-500">
				{customer?.email ?? ''}<br />
				{customer?.address ?? ''}
			</p>
		</div>
		<div>
			<p class="text-[11px] font-semibold tracking-wide text-slate-400 uppercase">Dates</p>
			<dl class="mt-2 space-y-1 text-xs">
				<div class="flex justify-between gap-3">
					<dt class="text-slate-400">Issued</dt>
					<dd class="text-slate-700">{formatDate(invoice.issueDate)}</dd>
				</div>
				<div class="flex justify-between gap-3">
					<dt class="text-slate-400">Due</dt>
					<dd class="text-slate-700">{formatDate(invoice.dueDate)}</dd>
				</div>
			</dl>
		</div>
		<div>
			<p class="text-[11px] font-semibold tracking-wide text-slate-400 uppercase">Reference</p>
			<dl class="mt-2 space-y-1 text-xs">
				<div class="flex justify-between gap-3">
					<dt class="text-slate-400">Subscription</dt>
					<dd class="text-slate-700">{subscription?.number ?? '—'}</dd>
				</div>
				<div class="flex justify-between gap-3">
					<dt class="text-slate-400">Currency</dt>
					<dd class="text-slate-700">USD</dd>
				</div>
			</dl>
		</div>
	</div>

	<div class="mt-8 overflow-x-auto">
		<table class="min-w-full text-sm">
			<thead>
				<tr class="border-b border-slate-200">
					<th
						class="pb-2 text-left text-[11px] font-semibold tracking-wide text-slate-400 uppercase"
						>Description</th
					>
					<th
						class="pb-2 text-right text-[11px] font-semibold tracking-wide text-slate-400 uppercase"
						>Qty</th
					>
					<th
						class="pb-2 text-right text-[11px] font-semibold tracking-wide text-slate-400 uppercase"
						>Unit price</th
					>
					<th
						class="pb-2 text-right text-[11px] font-semibold tracking-wide text-slate-400 uppercase"
						>Tax</th
					>
					<th
						class="pb-2 text-right text-[11px] font-semibold tracking-wide text-slate-400 uppercase"
						>Amount</th
					>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#each invoice.lines as line (line.id)}
					<tr>
						<td class="py-2.5 pr-3 text-slate-700">{line.description}</td>
						<td class="py-2.5 text-right text-slate-500">{line.quantity}</td>
						<td class="py-2.5 text-right text-slate-500">{currency(line.unitPrice)}</td>
						<td class="py-2.5 text-right text-slate-500">{taxRate(db.data, line.taxId)}%</td>
						<td class="py-2.5 text-right font-medium text-slate-800">
							{currency(line.quantity * line.unitPrice)}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div
		class="mt-6 flex flex-col gap-6 border-t border-slate-100 pt-5 sm:flex-row sm:justify-between"
	>
		<div class="max-w-xs text-xs leading-relaxed text-slate-500">
			{#if invoice.notes}
				<p class="text-[11px] font-semibold tracking-wide text-slate-400 uppercase">Notes</p>
				<p class="mt-1.5">{invoice.notes}</p>
			{/if}
			<p class="mt-3 text-[11px] text-slate-400">
				Payment via bank transfer, card, cash or UPI. Please reference {invoice.number}.
			</p>
		</div>

		<dl class="w-full max-w-xs space-y-1.5 text-sm">
			<div class="flex justify-between gap-4">
				<dt class="text-slate-500">Subtotal</dt>
				<dd class="text-slate-700">{currency(invoice.subtotal)}</dd>
			</div>
			{#if invoice.discountTotal > 0}
				<div class="flex justify-between gap-4 text-emerald-600">
					<dt>{invoice.discountName ?? 'Discount'}</dt>
					<dd>−{currency(invoice.discountTotal)}</dd>
				</div>
			{/if}
			<div class="flex justify-between gap-4">
				<dt class="text-slate-500">Tax</dt>
				<dd class="text-slate-700">{currency(invoice.taxTotal)}</dd>
			</div>
			<div
				class="flex justify-between gap-4 border-t border-slate-200 pt-2 text-base font-semibold"
			>
				<dt class="text-slate-900">Total</dt>
				<dd class="text-slate-900">{currency(invoice.total)}</dd>
			</div>
			<div class="flex justify-between gap-4">
				<dt class="text-slate-500">Amount paid</dt>
				<dd class="text-slate-700">{currency(invoice.amountPaid)}</dd>
			</div>
			<div class="flex justify-between gap-4 rounded-lg bg-slate-50 px-2 py-1.5 font-semibold">
				<dt class={balance > 0 ? 'text-rose-600' : 'text-emerald-600'}>
					{balance > 0 ? 'Balance due' : 'Paid in full'}
				</dt>
				<dd class={balance > 0 ? 'text-rose-600' : 'text-emerald-600'}>{currency(balance)}</dd>
			</div>
		</dl>
	</div>

	<p class="mt-8 border-t border-slate-100 pt-4 text-center text-[11px] text-slate-400">
		Thank you for choosing Brightloop. Questions? billing@brightloop.io
	</p>
</article>
