<script lang="ts">
	import { auth } from '#lib/auth/auth.svelte';
	import { db } from '#lib/data/store.svelte';
	import { setSubscriptionStatus } from '#lib/data/operations';
	import {
		customerById,
		planById,
		productById,
		subscriptionMonthlyValue
	} from '#lib/data/selectors';
	import type { Subscription } from '#lib/data/types';
	import { toasts } from '#lib/stores/toasts.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Card from '#lib/components/ui/Card.svelte';
	import EmptyState from '#lib/components/ui/EmptyState.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import { formatDate, paymentTermsLabel, relativeDays } from '#lib/utils/date';
	import { currency, titleCase } from '#lib/utils/format';

	let user = $derived(auth.user);
	let customer = $derived(customerById(db.data, user?.customerId ?? null));

	let subscriptions = $derived(
		customer
			? db.data.subscriptions
					.filter((subscription) => subscription.customerId === customer.id)
					.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
			: []
	);

	function toggle(subscription: Subscription) {
		const next = subscription.status === 'paused' ? 'active' : 'paused';
		const result = setSubscriptionStatus(subscription.id, next);
		if (!result.ok) {
			toasts.error(result.error ?? 'Could not update this service.');
			return;
		}
		toasts.success(
			next === 'paused' ? `${subscription.number} paused.` : `${subscription.number} resumed.`
		);
	}
</script>

<svelte:head>
	<title>My subscriptions · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader
		title="My subscriptions"
		description={customer
			? `Services for ${customer.company}. Pause or resume eligible services at any time.`
			: 'View and manage your services.'}
	>
		{#snippet actions()}
			<Button variant="outline" href="/portal/invoices">
				<Icon name="receipt" size={16} />
				My invoices
			</Button>
		{/snippet}
	</PageHeader>

	{#if subscriptions.length === 0}
		<Card>
			<EmptyState
				icon="repeat"
				title="No subscriptions yet"
				description="Your Brightloop services will appear here once they are set up."
			/>
		</Card>
	{:else}
		<div class="space-y-4">
			{#each subscriptions as subscription (subscription.id)}
				{@const plan = planById(db.data, subscription.planId)}
				{@const product = plan ? productById(db.data, plan.productId) : null}
				{@const value = subscriptionMonthlyValue(db.data, subscription)}
				<div
					class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-900/[0.03]"
				>
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div class="min-w-0">
							<div class="flex flex-wrap items-center gap-2">
								<h2 class="text-base font-semibold text-slate-900">
									{plan?.name ?? 'Subscription'}
								</h2>
								<StatusBadge status={subscription.status} />
							</div>
							<p class="mt-1 text-xs text-slate-400">
								{product?.name ?? 'Brightloop'} · {subscription.number}
							</p>
						</div>
						<div class="text-right">
							<p class="text-lg font-semibold tracking-tight text-slate-900">{currency(value)}</p>
							<p class="text-[11px] text-slate-400">
								{plan ? `${titleCase(plan.billingPeriod)} value` : 'Monthly value'}
							</p>
						</div>
					</div>

					<dl
						class="mt-5 grid gap-4 border-t border-slate-100 pt-4 text-sm sm:grid-cols-2 lg:grid-cols-4"
					>
						<div>
							<dt class="text-xs text-slate-400">Started</dt>
							<dd class="mt-1 text-slate-700">{formatDate(subscription.startDate)}</dd>
						</div>
						<div>
							<dt class="text-xs text-slate-400">Current term ends</dt>
							<dd class="mt-1 text-slate-700">{formatDate(subscription.endDate)}</dd>
						</div>
						<div>
							<dt class="text-xs text-slate-400">Next renewal</dt>
							<dd class="mt-1 text-slate-700">
								{subscription.status === 'active'
									? relativeDays(subscription.endDate)
									: 'Not active'}
							</dd>
						</div>
						<div>
							<dt class="text-xs text-slate-400">Payment terms</dt>
							<dd class="mt-1 text-slate-700">
								{paymentTermsLabel(subscription.paymentTerms)}
							</dd>
						</div>
					</dl>

					<div
						class="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4"
					>
						<p class="text-xs text-slate-400">
							{subscription.lines.length} billed line(s) · {plan
								? titleCase(plan.billingPeriod)
								: 'Recurring'} service
						</p>
						<div class="flex items-center gap-2">
							{#if subscription.status === 'active' && plan?.pausable}
								<Button variant="outline" size="sm" onclick={() => toggle(subscription)}>
									<Icon name="pause" size={14} />
									Pause service
								</Button>
							{:else if subscription.status === 'paused'}
								<Button variant="success" size="sm" onclick={() => toggle(subscription)}>
									<Icon name="play" size={14} />
									Resume service
								</Button>
							{:else if subscription.status === 'active'}
								<p class="text-xs text-slate-400">This plan cannot be paused online.</p>
							{/if}
							<Button variant="ghost" size="sm" href="/portal/invoices">
								Invoices
								<Icon name="arrow-right" size={14} />
							</Button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
