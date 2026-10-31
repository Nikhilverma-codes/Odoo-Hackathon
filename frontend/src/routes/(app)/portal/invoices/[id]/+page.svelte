<script lang="ts">
	import { page } from '$app/state';
	import { auth } from '#lib/auth/auth.svelte';
	import { db } from '#lib/data/store.svelte';
	import { customerById, invoiceBalance, invoiceState, isOverdue } from '#lib/data/selectors';
	import Button from '#lib/components/ui/Button.svelte';
	import Card from '#lib/components/ui/Card.svelte';
	import EmptyState from '#lib/components/ui/EmptyState.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import InvoiceDocument from '#lib/components/InvoiceDocument.svelte';
	import { formatDate } from '#lib/utils/date';
	import { currency, titleCase } from '#lib/utils/format';

	let user = $derived(auth.user);
	let customer = $derived(customerById(db.data, user?.customerId ?? null));

	let invoice = $derived(
		db.data.invoices.find(
			(item) =>
				item.id === page.params.id &&
				item.customerId === user?.customerId &&
				item.status !== 'draft'
		) ?? null
	);

	let payments = $derived(
		db.data.payments
			.filter((payment) => payment.invoiceId === invoice?.id)
			.sort((a, b) => b.date.localeCompare(a.date))
	);

	let status = $derived(invoice ? invoiceState(invoice) : 'confirmed');
	let balance = $derived(invoice ? invoiceBalance(invoice) : 0);
</script>

<svelte:head>
	<title>{invoice?.number ?? 'Invoice'} · Brightloop</title>
</svelte:head>

{#if invoice}
	<div class="space-y-6">
		<PageHeader
			title={invoice.number}
			description={`${customer?.company ?? 'Your account'} · issued ${formatDate(invoice.issueDate)}`}
			backHref="/portal/invoices"
			backLabel="My invoices"
			class="print:hidden"
		>
			{#snippet actions()}
				<StatusBadge {status} />
				<Button variant="outline" onclick={() => window.print()}>
					<Icon name="printer" size={16} />
					Print
				</Button>
			{/snippet}
		</PageHeader>

		<div class="grid gap-6 xl:grid-cols-3">
			<div class="xl:col-span-2">
				<InvoiceDocument {invoice} />
			</div>

			<div class="space-y-5 print:hidden">
				<Card>
					<div class="flex items-center justify-between">
						<h2 class="text-sm font-semibold text-slate-900">Invoice summary</h2>
						<StatusBadge {status} />
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
				</Card>

				<Card>
					<h2 class="text-sm font-semibold text-slate-900">Payment instructions</h2>
					<p class="mt-2 text-xs leading-relaxed text-slate-500">
						Pay by bank transfer, card, cash or UPI. Include invoice number
						<strong class="text-slate-700">{invoice.number}</strong> with your payment. Brightloop will
						mark the invoice as paid once payment is received.
					</p>
				</Card>

				<Card padded={false}>
					<div class="flex items-center justify-between px-5 py-4">
						<div>
							<h2 class="text-sm font-semibold text-slate-900">Payments</h2>
							<p class="text-xs text-slate-400">{payments.length} recorded</p>
						</div>
					</div>

					{#if payments.length === 0}
						<div class="border-t border-slate-100">
							<EmptyState
								icon="wallet"
								title="No payments yet"
								description="Payments recorded against this invoice will appear here."
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
			description="This invoice does not exist or is not available on your account."
		>
			{#snippet action()}
				<Button href="/portal/invoices" variant="outline">Back to my invoices</Button>
			{/snippet}
		</EmptyState>
	</Card>
{/if}
