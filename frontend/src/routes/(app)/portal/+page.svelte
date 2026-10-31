<script lang="ts">
	import { auth } from '#lib/auth/auth.svelte';
	import { db } from '#lib/data/store.svelte';
	import {
		customerById,
		invoiceBalance,
		invoiceState,
		planById,
		productById,
		subscriptionMonthlyValue
	} from '#lib/data/selectors';
	import Button from '#lib/components/ui/Button.svelte';
	import Card from '#lib/components/ui/Card.svelte';
	import EmptyState from '#lib/components/ui/EmptyState.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import StatCard from '#lib/components/ui/StatCard.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import { formatDate, relativeDays } from '#lib/utils/date';
	import { currency, sum, titleCase } from '#lib/utils/format';

	let user = $derived(auth.user);
	let customer = $derived(customerById(db.data, user?.customerId ?? null));

	let subscriptions = $derived(
		customer
			? db.data.subscriptions
					.filter((subscription) => subscription.customerId === customer.id)
					.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
			: []
	);

	let activeSubscriptions = $derived(
		subscriptions.filter((subscription) => subscription.status === 'active')
	);

	let activeServices = $derived(activeSubscriptions.length);

	let monthlySpend = $derived(
		sum(activeSubscriptions.map((subscription) => subscriptionMonthlyValue(db.data, subscription)))
	);

	let invoices = $derived(
		customer
			? db.data.invoices
					.filter((invoice) => invoice.customerId === customer.id && invoice.status !== 'draft')
					.sort((a, b) => b.issueDate.localeCompare(a.issueDate))
			: []
	);

	let openInvoices = $derived(
		invoices.filter((invoice) => invoice.status !== 'cancelled' && invoiceBalance(invoice) > 0)
	);

	let outstanding = $derived(sum(openInvoices.map(invoiceBalance)));
	let recentInvoices = $derived(invoices.slice(0, 5));

	let nextRenewal = $derived(
		activeSubscriptions
			.slice()
			.sort((a, b) => a.endDate.localeCompare(b.endDate))
			.at(0) ?? null
	);
</script>

<svelte:head>
	<title>My services · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader
		title={`Hello, ${user?.name.split(' ')[0] ?? 'there'}`}
		description={customer
			? `${customer.company} · manage your services, invoices and billing.`
			: 'Manage your services and billing.'}
	>
		{#snippet actions()}
			<Button variant="outline" href="/portal/invoices">
				<Icon name="receipt" size={16} />
				My invoices
			</Button>
			<Button href="/portal/subscriptions">
				<Icon name="repeat" size={16} />
				My subscriptions
			</Button>
		{/snippet}
	</PageHeader>

	<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
		<StatCard
			label="Active services"
			value={String(activeServices)}
			icon="repeat"
			tone="brand"
			hint={`${subscriptions.length} total service(s)`}
		/>
		<StatCard
			label="Monthly spend"
			value={currency(monthlySpend)}
			icon="credit-card"
			tone="violet"
			hint="Active services only"
		/>
		<StatCard
			label="Outstanding"
			value={currency(outstanding)}
			icon="receipt"
			tone={outstanding > 0 ? 'amber' : 'emerald'}
			hint={`${openInvoices.length} open invoice(s)`}
		/>
		<StatCard
			label="Next renewal"
			value={nextRenewal ? formatDate(nextRenewal.endDate) : 'None'}
			icon="calendar"
			tone="sky"
			hint={nextRenewal ? relativeDays(nextRenewal.endDate) : 'No active renewals'}
		/>
	</div>

	<div class="grid gap-5 xl:grid-cols-3">
		<div class="space-y-5 xl:col-span-2">
			<Card padded={false}>
				<div class="flex items-center justify-between gap-3 px-5 py-4">
					<div>
						<h2 class="text-sm font-semibold text-slate-900">Your services</h2>
						<p class="text-xs text-slate-400">Subscriptions linked to your account</p>
					</div>
					<Button variant="ghost" size="sm" href="/portal/subscriptions">
						View all
						<Icon name="arrow-right" size={14} />
					</Button>
				</div>

				{#if subscriptions.length === 0}
					<div class="border-t border-slate-100">
						<EmptyState
							icon="repeat"
							title="No services yet"
							description="Your Brightloop services will appear here once they are set up."
						/>
					</div>
				{:else}
					<ul class="divide-y divide-slate-100 border-t border-slate-100">
						{#each subscriptions.slice(0, 4) as subscription (subscription.id)}
							{@const plan = planById(db.data, subscription.planId)}
							{@const product = plan ? productById(db.data, plan.productId) : null}
							<li class="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center">
								<div class="min-w-0 flex-1">
									<div class="flex flex-wrap items-center gap-2">
										<p class="font-medium text-slate-800">{plan?.name ?? 'Service'}</p>
										<StatusBadge status={subscription.status} />
									</div>
									<p class="mt-0.5 truncate text-xs text-slate-400">
										{product?.name ?? 'Brightloop'} · {subscription.number}
									</p>
									<p class="mt-1 text-xs text-slate-400">
										{formatDate(subscription.startDate)} to {formatDate(subscription.endDate)}
									</p>
								</div>
								<div class="flex items-center justify-between gap-4 sm:justify-end">
									<div class="text-right">
										<p class="text-sm font-semibold text-slate-800">
											{currency(subscriptionMonthlyValue(db.data, subscription))}
										</p>
										<p class="text-[11px] text-slate-400">
											{plan ? titleCase(plan.billingPeriod) : 'Billing'} value
										</p>
									</div>
									<Button
										variant="ghost"
										size="icon"
										title="Manage subscription"
										href="/portal/subscriptions"
									>
										<Icon name="arrow-right" size={15} />
									</Button>
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</Card>

			<Card padded={false}>
				<div class="flex items-center justify-between gap-3 px-5 py-4">
					<div>
						<h2 class="text-sm font-semibold text-slate-900">Recent invoices</h2>
						<p class="text-xs text-slate-400">Your latest billing activity</p>
					</div>
					<Button variant="ghost" size="sm" href="/portal/invoices">
						View all
						<Icon name="arrow-right" size={14} />
					</Button>
				</div>

				{#if recentInvoices.length === 0}
					<div class="border-t border-slate-100">
						<EmptyState
							icon="receipt"
							title="No invoices yet"
							description="Invoices issued to your account will appear here."
						/>
					</div>
				{:else}
					<ul class="divide-y divide-slate-100 border-t border-slate-100">
						{#each recentInvoices as invoice (invoice.id)}
							<li>
								<a
									href={`/portal/invoices/${invoice.id}`}
									class="flex items-center gap-3 px-5 py-3.5 transition hover:bg-slate-50"
								>
									<div class="min-w-0 flex-1">
										<p class="text-sm font-medium text-slate-800">{invoice.number}</p>
										<p class="text-xs text-slate-400">
											Issued {formatDate(invoice.issueDate)} · due {formatDate(invoice.dueDate)}
										</p>
									</div>
									<StatusBadge status={invoiceState(invoice)} />
									<div class="w-24 text-right">
										<p class="text-sm font-medium text-slate-700">{currency(invoice.total)}</p>
										<p class="text-[11px] text-slate-400">
											{invoiceBalance(invoice) > 0
												? `${currency(invoiceBalance(invoice))} due`
												: 'Paid'}
										</p>
									</div>
									<Icon name="arrow-right" size={15} class="text-slate-400" />
								</a>
							</li>
						{/each}
					</ul>
				{/if}
			</Card>
		</div>

		<div class="space-y-5">
			<Card>
				<h2 class="text-sm font-semibold text-slate-900">Account details</h2>
				{#if customer}
					<dl class="mt-4 space-y-3 text-sm">
						<div>
							<dt class="text-xs text-slate-400">Company</dt>
							<dd class="mt-0.5 font-medium text-slate-700">{customer.company}</dd>
						</div>
						<div>
							<dt class="text-xs text-slate-400">Contact</dt>
							<dd class="mt-0.5 text-slate-700">{customer.name}</dd>
						</div>
						<div>
							<dt class="text-xs text-slate-400">Email</dt>
							<dd class="mt-0.5 break-all text-slate-700">{customer.email}</dd>
						</div>
						{#if customer.phone}
							<div>
								<dt class="text-xs text-slate-400">Phone</dt>
								<dd class="mt-0.5 text-slate-700">{customer.phone}</dd>
							</div>
						{/if}
						{#if customer.address}
							<div>
								<dt class="text-xs text-slate-400">Billing address</dt>
								<dd class="mt-0.5 leading-relaxed text-slate-700">{customer.address}</dd>
							</div>
						{/if}
						<div class="border-t border-slate-100 pt-3">
							<dt class="text-xs text-slate-400">Customer since</dt>
							<dd class="mt-0.5 text-slate-700">{formatDate(customer.since)}</dd>
						</div>
					</dl>
				{:else}
					<p class="mt-2 text-sm text-slate-500">No customer profile is linked to this account.</p>
				{/if}
			</Card>

			<Card>
				<div class="flex items-start gap-3">
					<div
						class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600"
					>
						<Icon name="wallet" size={18} />
					</div>
					<div>
						<h2 class="text-sm font-semibold text-slate-900">Billing support</h2>
						<p class="mt-1 text-xs leading-relaxed text-slate-500">
							Questions about an invoice or payment? Contact billing@brightloop.io and include the
							invoice number.
						</p>
					</div>
				</div>
			</Card>
		</div>
	</div>
</div>
