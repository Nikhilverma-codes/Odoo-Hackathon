<script lang="ts">
	import { page } from '$app/state';
	import { cancelInvoice, confirmInvoice } from '#lib/data/operations';
	import { db } from '#lib/data/store.svelte';
	import { customerById, invoiceBalance, invoiceState, isOverdue } from '#lib/data/selectors';
	import Button from '#lib/components/ui/Button.svelte';
	import Card from '#lib/components/ui/Card.svelte';
	import ConfirmDialog from '#lib/components/ui/ConfirmDialog.svelte';
	import EmptyState from '#lib/components/ui/EmptyState.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import InvoiceDocument from '#lib/components/InvoiceDocument.svelte';
	import PaymentModal from '#lib/components/PaymentModal.svelte';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { formatDate, paymentTermsLabel, relativeDays } from '#lib/utils/date';
	import { currency, titleCase } from '#lib/utils/format';

	let invoice = $derived(db.data.invoices.find((item) => item.id === page.params.id) ?? null);
	let customer = $derived(customerById(db.data, invoice?.customerId ?? null));
	let subscription = $derived(
		db.data.subscriptions.find((item) => item.id === invoice?.subscriptionId) ?? null
	);
	let payments = $derived(
		db.data.payments
			.filter((payment) => payment.invoiceId === invoice?.id)
			.sort((a, b) => b.date.localeCompare(a.date))
	);

	let invoiceStatus = $derived(invoice ? invoiceState(invoice) : 'draft');
	let balance = $derived(invoice ? invoiceBalance(invoice) : 0);

	let paymentOpen = $state(false);
	let cancelOpen = $state(false);
	let working = $state(false);

	function confirm() {
		if (!invoice) return;
		const result = confirmInvoice(invoice.id);
		if (!result.ok) {
			toasts.error(result.error ?? 'Could not confirm the invoice.');
			return;
		}
		toasts.success(`${invoice.number} confirmed.`);
	}

	function cancel() {
		if (!invoice) return;
		working = true;
		const result = cancelInvoice(invoice.id);
		working = false;
		cancelOpen = false;
		if (!result.ok) {
			toasts.error(result.error ?? 'Could not cancel the invoice.');
			return;
		}
		toasts.success(`${invoice.number} cancelled.`);
	}
</script>

<svelte:head>
	<title>{invoice?.number ?? 'Invoice'} · Brightloop</title>
</svelte:head>

{#if invoice}
	<div class="space-y-6">
		<PageHeader
			title={invoice.number}
			description={`${customer?.company ?? 'Customer'} · ${paymentTermsLabel(subscription?.paymentTerms ?? 'due_on_receipt')}`}
			backHref="/invoices"
			backLabel="Invoices"
			class="print:hidden"
		>
			{#snippet actions()}
				<StatusBadge status={invoiceStatus} />
				<Button variant="outline" onclick={() => window.print()}>
					<Icon name="printer" size={16} />
					Print
				</Button>
				{#if invoice.status === 'draft'}
					<Button onclick={confirm}>
						<Icon name="check" size={16} />
						Confirm invoice
					</Button>
				{/if}
				{#if balance > 0 && invoice.status !== 'cancelled'}
					<Button onclick={() => (paymentOpen = true)}>
						<Icon name="wallet" size={16} />
						Record payment
					</Button>
				{/if}
				{#if invoice.status !== 'paid' && invoice.status !== 'cancelled'}
					<Button
						variant="ghost"
						class="text-rose-600 hover:bg-rose-50"
						onclick={() => (cancelOpen = true)}
					>
						Cancel
					</Button>
				{/if}
			{/snippet}
		</PageHeader>

		<div class="grid gap-6 xl:grid-cols-3">
			<div class="xl:col-span-2">
				<InvoiceDocument {invoice} />
			</div>

			<div class="space-y-5 print:hidden">
				<Card>
					<div class="flex items-center justify-between">
						<h2 class="text-sm font-semibold text-slate-900">At a glance</h2>
						<StatusBadge status={invoiceStatus} />
					</div>
					<dl class="mt-4 space-y-3 text-sm">
						<div class="flex items-center justify-between">
							<dt class="text-slate-400">Issue date</dt>
							<dd class="text-slate-700">{formatDate(invoice.issueDate)}</dd>
						</div>
						<div class="flex items-center justify-between">
							<dt class="text-slate-400">Due date</dt>
							<dd class={isOverdue(invoice) ? 'font-medium text-rose-600' : 'text-slate-700'}>
								{formatDate(invoice.dueDate)}
							</dd>
						</div>
						<div class="flex items-center justify-between">
							<dt class="text-slate-400">Total</dt>
							<dd class="font-medium text-slate-800">{currency(invoice.total)}</dd>
						</div>
						<div class="flex items-center justify-between">
							<dt class="text-slate-400">Paid</dt>
							<dd class="text-slate-700">{currency(invoice.amountPaid)}</dd>
						</div>
						<div class="flex items-center justify-between border-t border-slate-100 pt-3">
							<dt class="font-medium text-slate-700">Balance</dt>
							<dd
								class={balance > 0
									? 'font-semibold text-rose-600'
									: 'font-semibold text-emerald-600'}
							>
								{currency(balance)}
							</dd>
						</div>
					</dl>
					{#if invoiceStatus === 'overdue'}
						<p class="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">
							Overdue by {formatDate(invoice.dueDate)} ({relativeDays(invoice.dueDate)}).
						</p>
					{/if}
					{#if subscription}
						<a
							href={`/subscriptions/${subscription.id}`}
							class="mt-3 flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-500 transition hover:border-brand-200 hover:text-brand-700"
						>
							<span>{subscription.number}</span>
							<Icon name="arrow-right" size={14} />
						</a>
					{/if}
					{#if customer}
						<a
							href={`/customers/${customer.id}`}
							class="mt-2 flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-500 transition hover:border-brand-200 hover:text-brand-700"
						>
							<span>{customer.company}</span>
							<Icon name="arrow-right" size={14} />
						</a>
					{/if}
				</Card>

				<Card padded={false}>
					<div class="flex items-center justify-between px-5 py-4">
						<div>
							<h2 class="text-sm font-semibold text-slate-900">Payments</h2>
							<p class="text-xs text-slate-400">{payments.length} recorded</p>
						</div>
						{#if balance > 0 && invoice.status !== 'cancelled'}
							<Button variant="ghost" size="sm" onclick={() => (paymentOpen = true)}>
								<Icon name="plus" size={14} />
								Add
							</Button>
						{/if}
					</div>

					{#if payments.length === 0}
						<div class="border-t border-slate-100">
							<EmptyState
								icon="wallet"
								title="No payments yet"
								description="Payments recorded against this invoice appear here."
							/>
						</div>
					{:else}
						<ul class="divide-y divide-slate-100 border-t border-slate-100">
							{#each payments as payment (payment.id)}
								<li class="flex items-start justify-between gap-3 px-5 py-3">
									<div class="min-w-0">
										<p class="text-sm font-medium text-slate-800">{currency(payment.amount)}</p>
										<p class="text-xs text-slate-400">
											{titleCase(payment.method)} · {formatDate(payment.date)}
										</p>
										{#if payment.note}
											<p class="mt-0.5 truncate text-[11px] text-slate-400">{payment.note}</p>
										{/if}
									</div>
									<Icon name="check-circle" size={16} class="mt-0.5 shrink-0 text-emerald-500" />
								</li>
							{/each}
						</ul>
					{/if}
				</Card>
			</div>
		</div>
	</div>
{:else}
	<Card>
		<EmptyState
			icon="receipt"
			title="Invoice not found"
			description="This invoice may have been removed."
		>
			{#snippet action()}
				<Button href="/invoices" variant="outline">Back to invoices</Button>
			{/snippet}
		</EmptyState>
	</Card>
{/if}

<PaymentModal open={paymentOpen} {invoice} onclose={() => (paymentOpen = false)} />

<ConfirmDialog
	open={cancelOpen}
	title="Cancel invoice"
	message="Cancel this invoice? It will no longer be collectible."
	confirmLabel="Cancel invoice"
	loading={working}
	onconfirm={cancel}
	oncancel={() => (cancelOpen = false)}
/>
