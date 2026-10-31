<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { db } from '#lib/data/store.svelte';
	import { generateInvoice, renewSubscription, setSubscriptionStatus } from '#lib/data/operations';
	import {
		customerById,
		invoiceBalance,
		invoiceState,
		planById,
		productById,
		subscriptionTotal,
		taxRate
	} from '#lib/data/selectors';
	import type { SubscriptionStatus } from '#lib/data/types';
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Card from '#lib/components/ui/Card.svelte';
	import ConfirmDialog from '#lib/components/ui/ConfirmDialog.svelte';
	import EmptyState from '#lib/components/ui/EmptyState.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { formatDate, paymentTermsLabel, relativeDays, daysBetween } from '#lib/utils/date';
	import { cn, currency, titleCase } from '#lib/utils/format';

	const steps: { status: SubscriptionStatus; label: string; description: string }[] = [
		{ status: 'draft', label: 'Draft', description: 'Prepared internally' },
		{ status: 'quotation', label: 'Quotation', description: 'Sent to customer' },
		{ status: 'confirmed', label: 'Confirmed', description: 'Customer accepted' },
		{ status: 'active', label: 'Active', description: 'Billing in progress' },
		{ status: 'closed', label: 'Closed', description: 'Contract ended' }
	];

	let subscription = $derived(
		db.data.subscriptions.find((item) => item.id === page.params.id) ?? null
	);
	let customer = $derived(customerById(db.data, subscription?.customerId ?? null));
	let plan = $derived(planById(db.data, subscription?.planId ?? null));
	let invoices = $derived(
		db.data.invoices
			.filter((invoice) => invoice.subscriptionId === subscription?.id)
			.sort((a, b) => b.issueDate.localeCompare(a.issueDate))
	);

	let stepIndex = $derived(
		subscription
			? subscription.status === 'paused'
				? 3
				: steps.findIndex((step) => step.status === subscription?.status)
			: 0
	);

	let total = $derived(subscription ? subscriptionTotal(subscription) : 0);
	let durationDays = $derived(
		subscription ? daysBetween(subscription.startDate, subscription.endDate) : 0
	);

	let closeOpen = $state(false);

	async function changeStatus(status: SubscriptionStatus) {
		if (!subscription) return;
		const result = await setSubscriptionStatus(subscription.id, status);
		if (!result.ok) {
			toasts.error(result.error ?? 'Could not update the subscription.');
			return;
		}
		toasts.success(`Subscription marked as ${status}.`);
		closeOpen = false;
	}

	async function renew() {
		if (!subscription) return;
		const result = await renewSubscription(subscription.id);
		if (!result.ok) {
			toasts.error(result.error ?? 'Could not renew the subscription.');
			return;
		}
		const end = result.subscription?.endDate;
		toasts.success(end ? `Renewed until ${formatDate(end)}.` : 'Subscription renewed.');
	}

	async function createInvoice() {
		if (!subscription) return;
		const result = await generateInvoice(subscription.id);
		if (!result.ok) {
			toasts.error(result.error);
			return;
		}
		toasts.success(`${result.invoice.number} created as a draft.`);
		await goto(`/invoices/${result.invoice.id}`);
	}

	function productLabel(productId: string, variantId: string | null): string {
		const product = productById(db.data, productId);
		if (!product) return 'Product';
		const variant = product.variants.find((item) => item.id === variantId);
		return variant ? `${product.name} — ${variant.name}` : product.name;
	}
</script>

<svelte:head>
	<title>{subscription?.number ?? 'Subscription'} · Brightloop</title>
</svelte:head>

{#if subscription}
	<div class="space-y-6">
		<PageHeader
			title={subscription.number}
			description={`${customer?.company ?? 'Customer'} · ${plan?.name ?? 'No plan'}`}
			backHref="/subscriptions"
			backLabel="Subscriptions"
		>
			{#snippet actions()}
				<StatusBadge status={subscription.status} />
				{#if subscription.status === 'draft'}
					<Button onclick={() => changeStatus('quotation')}>
						<Icon name="file-text" size={16} />
						Send quotation
					</Button>
				{:else if subscription.status === 'quotation'}
					<Button onclick={() => changeStatus('confirmed')}>
						<Icon name="check" size={16} />
						Confirm
					</Button>
				{:else if subscription.status === 'confirmed'}
					<Button onclick={() => changeStatus('active')}>
						<Icon name="play" size={16} />
						Activate
					</Button>
				{:else if subscription.status === 'active'}
					<Button onclick={createInvoice}>
						<Icon name="receipt" size={16} />
						Generate invoice
					</Button>
					{#if plan?.renewable}
						<Button variant="outline" onclick={renew}>
							<Icon name="repeat" size={16} />
							Renew
						</Button>
					{/if}
					{#if plan?.pausable}
						<Button variant="outline" onclick={() => changeStatus('paused')}>
							<Icon name="pause" size={16} />
							Pause
						</Button>
					{/if}
					{#if plan?.allowEarlyClose || plan?.autoClose}
						<Button
							variant="ghost"
							class="text-rose-600 hover:bg-rose-50"
							onclick={() => (closeOpen = true)}
						>
							Close
						</Button>
					{/if}
				{:else if subscription.status === 'paused'}
					<Button onclick={() => changeStatus('active')}>
						<Icon name="play" size={16} />
						Resume
					</Button>
					{#if plan?.allowEarlyClose || plan?.autoClose}
						<Button
							variant="ghost"
							class="text-rose-600 hover:bg-rose-50"
							onclick={() => (closeOpen = true)}
						>
							Close
						</Button>
					{/if}
				{/if}
			{/snippet}
		</PageHeader>

		<Card>
			<ol class="flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-0">
				{#each steps as step, index (step.status)}
					{@const done = index < stepIndex}
					{@const current = index === stepIndex}
					<li class="flex flex-1 items-start gap-3 sm:flex-col sm:gap-2">
						<div class="flex items-center gap-2 sm:w-full">
							<span
								class={cn(
									'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold',
									done && 'border-brand-600 bg-brand-600 text-white',
									current && 'border-brand-600 bg-white text-brand-700 ring-4 ring-brand-100',
									!done && !current && 'border-slate-300 bg-white text-slate-400'
								)}
							>
								{#if done}
									<Icon name="check" size={13} stroke={2.6} />
								{:else}
									{index + 1}
								{/if}
							</span>
							{#if index < steps.length - 1}
								<span class="hidden h-px flex-1 bg-slate-200 sm:block">
									<span class={cn('block h-px', done && 'bg-brand-500')}></span>
								</span>
							{/if}
						</div>
						<div class="sm:pr-4">
							<p
								class={cn(
									'text-xs font-semibold',
									current ? 'text-brand-700' : done ? 'text-slate-700' : 'text-slate-400'
								)}
							>
								{step.label}
								{#if current && subscription.status === 'paused'}
									<span class="ml-1 text-amber-600">(paused)</span>
								{/if}
							</p>
							<p class="text-[11px] text-slate-400">{step.description}</p>
						</div>
					</li>
				{/each}
			</ol>
		</Card>

		<div class="grid gap-6 xl:grid-cols-3">
			<Card>
				<div class="flex items-center gap-3">
					<Avatar name={customer?.company ?? 'Customer'} size="md" />
					<div class="min-w-0">
						<a
							href={`/customers/${customer?.id ?? ''}`}
							class="block truncate text-sm font-semibold text-slate-900 hover:text-brand-600"
						>
							{customer?.company ?? 'Unknown customer'}
						</a>
						<p class="truncate text-xs text-slate-400">{customer?.name ?? ''}</p>
					</div>
				</div>

				<dl class="mt-5 space-y-3 text-sm">
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Plan</dt>
						<dd class="text-right font-medium text-slate-700">{plan?.name ?? '—'}</dd>
					</div>
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Billing</dt>
						<dd class="text-right text-slate-700">{plan ? titleCase(plan.billingPeriod) : '—'}</dd>
					</div>
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Payment terms</dt>
						<dd class="text-right text-slate-700">
							{paymentTermsLabel(subscription.paymentTerms)}
						</dd>
					</div>
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Start</dt>
						<dd class="text-right text-slate-700">{formatDate(subscription.startDate)}</dd>
					</div>
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">End</dt>
						<dd class="text-right text-slate-700">
							{formatDate(subscription.endDate)}
							<span class="block text-[11px] text-slate-400"
								>{relativeDays(subscription.endDate)}</span
							>
						</dd>
					</div>
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Duration</dt>
						<dd class="text-right text-slate-700">{durationDays} days</dd>
					</div>
				</dl>

				{#if subscription.notes}
					<div class="mt-4 rounded-lg bg-slate-50 px-3 py-2">
						<p class="text-[11px] tracking-wide text-slate-400 uppercase">Notes</p>
						<p class="mt-1 text-xs text-slate-600">{subscription.notes}</p>
					</div>
				{/if}
			</Card>

			<Card class="xl:col-span-2" padded={false}>
				<div class="flex items-center justify-between px-5 py-4">
					<div>
						<h2 class="text-sm font-semibold text-slate-900">Line items</h2>
						<p class="text-xs text-slate-400">
							{subscription.lines.length} line(s) on this contract
						</p>
					</div>
					<p class="text-lg font-semibold text-slate-900">{currency(total)}</p>
				</div>
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-slate-100 text-sm">
						<thead class="bg-slate-50">
							<tr>
								<th
									class="px-5 py-2.5 text-left text-[11px] font-semibold tracking-wide text-slate-500 uppercase"
									>Item</th
								>
								<th
									class="px-4 py-2.5 text-right text-[11px] font-semibold tracking-wide text-slate-500 uppercase"
									>Qty</th
								>
								<th
									class="px-4 py-2.5 text-right text-[11px] font-semibold tracking-wide text-slate-500 uppercase"
									>Unit price</th
								>
								<th
									class="px-4 py-2.5 text-right text-[11px] font-semibold tracking-wide text-slate-500 uppercase"
									>Tax</th
								>
								<th
									class="px-5 py-2.5 text-right text-[11px] font-semibold tracking-wide text-slate-500 uppercase"
									>Amount</th
								>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							{#each subscription.lines as line (line.id)}
								<tr>
									<td class="px-5 py-3">
										<p class="font-medium text-slate-800">
											{productLabel(line.productId, line.variantId)}
										</p>
										<p class="text-[11px] text-slate-400">
											{productById(db.data, line.productId)?.type ?? 'Product'}
										</p>
									</td>
									<td class="px-4 py-3 text-right text-slate-600">{line.quantity}</td>
									<td class="px-4 py-3 text-right text-slate-600">{currency(line.unitPrice)}</td>
									<td class="px-4 py-3 text-right text-slate-500"
										>{taxRate(db.data, line.taxId)}%</td
									>
									<td class="px-5 py-3 text-right font-medium text-slate-800">
										{currency(line.quantity * line.unitPrice)}
									</td>
								</tr>
							{/each}
						</tbody>
						<tfoot class="bg-slate-50">
							<tr>
								<td colspan={4} class="px-5 py-2.5 text-right text-xs text-slate-500"
									>Recurring total</td
								>
								<td class="px-5 py-2.5 text-right font-semibold text-slate-900"
									>{currency(total)}</td
								>
							</tr>
						</tfoot>
					</table>
				</div>
			</Card>
		</div>

		<Card padded={false}>
			<div class="flex items-center justify-between px-5 py-4">
				<div>
					<h2 class="text-sm font-semibold text-slate-900">Invoices</h2>
					<p class="text-xs text-slate-400">Billing generated from this subscription</p>
				</div>
				{#if subscription.status === 'active'}
					<Button variant="outline" size="sm" onclick={createInvoice}>
						<Icon name="plus" size={14} />
						New invoice
					</Button>
				{/if}
			</div>
			<Table
				columns={[
					{ label: 'Invoice' },
					{ label: 'Issued' },
					{ label: 'Due' },
					{ label: 'Status' },
					{ label: 'Total', align: 'right' },
					{ label: 'Balance', align: 'right' },
					{ label: '', align: 'right' }
				]}
				rowCount={invoices.length}
				class="rounded-none border-0 shadow-none"
				emptyTitle="No invoices yet"
				emptyDescription="Generate an invoice once the subscription is confirmed."
				emptyIcon="receipt"
			>
				{#each invoices as invoice (invoice.id)}
					<tr class="transition hover:bg-slate-50">
						<td class="px-4 py-3">
							<a
								href={`/invoices/${invoice.id}`}
								class="font-medium text-slate-800 hover:text-brand-600"
							>
								{invoice.number}
							</a>
						</td>
						<td class="px-4 py-3 text-slate-500">{formatDate(invoice.issueDate)}</td>
						<td class="px-4 py-3 text-slate-500">{formatDate(invoice.dueDate)}</td>
						<td class="px-4 py-3"><StatusBadge status={invoiceState(invoice)} /></td>
						<td class="px-4 py-3 text-right font-medium text-slate-700"
							>{currency(invoice.total)}</td
						>
						<td class="px-4 py-3 text-right">
							<span class={invoiceBalance(invoice) > 0 ? 'text-rose-600' : 'text-slate-400'}>
								{currency(invoiceBalance(invoice))}
							</span>
						</td>
						<td class="px-4 py-3 text-right">
							<Button
								variant="ghost"
								size="icon"
								href={`/invoices/${invoice.id}`}
								title="View invoice"
							>
								<Icon name="arrow-right" size={15} />
							</Button>
						</td>
					</tr>
				{/each}
			</Table>
		</Card>
	</div>
{:else}
	<Card>
		<EmptyState
			icon="repeat"
			title="Subscription not found"
			description="This subscription may have been removed."
		>
			{#snippet action()}
				<Button href="/subscriptions" variant="outline">Back to subscriptions</Button>
			{/snippet}
		</EmptyState>
	</Card>
{/if}

<ConfirmDialog
	open={closeOpen}
	title="Close subscription"
	message="Close this subscription now? Billing will stop and the contract cannot be reactivated."
	confirmLabel="Close subscription"
	onconfirm={() => changeStatus('closed')}
	oncancel={() => (closeOpen = false)}
/>
