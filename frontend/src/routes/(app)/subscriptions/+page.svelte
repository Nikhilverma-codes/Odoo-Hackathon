<script lang="ts">
	import { db } from '#lib/data/store.svelte';
	import type { SubscriptionStatus } from '#lib/data/types';
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Badge from '#lib/components/ui/Badge.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import Input from '#lib/components/ui/Input.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import Pagination from '#lib/components/ui/Pagination.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import {
		customerById,
		planById,
		subscriptionMonthlyValue,
		subscriptionTotal
	} from '#lib/data/selectors';
	import { daysUntil, formatDate, relativeDays } from '#lib/utils/date';
	import { currency, titleCase } from '#lib/utils/format';

	type Filter = 'all' | SubscriptionStatus;

	const statuses: SubscriptionStatus[] = [
		'draft',
		'quotation',
		'confirmed',
		'active',
		'paused',
		'closed'
	];

	let search = $state('');
	let filter = $state<Filter>('all');
	let page = $state(1);
	const pageSize = 8;

	let counts = $derived(
		Object.fromEntries(
			statuses.map((status) => [
				status,
				db.data.subscriptions.filter((subscription) => subscription.status === status).length
			])
		) as Record<SubscriptionStatus, number>
	);

	let rows = $derived(
		db.data.subscriptions
			.map((subscription) => ({
				subscription,
				customer: customerById(db.data, subscription.customerId),
				plan: planById(db.data, subscription.planId),
				value: subscriptionMonthlyValue(db.data, subscription)
			}))
			.filter((row) => {
				const matchesFilter = filter === 'all' || row.subscription.status === filter;
				const haystack =
					`${row.subscription.number} ${row.customer?.company ?? ''} ${row.customer?.name ?? ''} ${row.plan?.name ?? ''}`.toLowerCase();
				return matchesFilter && haystack.includes(search.trim().toLowerCase());
			})
			.sort((a, b) => b.subscription.createdAt.localeCompare(a.subscription.createdAt))
	);

	let paged = $derived(rows.slice((page - 1) * pageSize, page * pageSize));

	$effect(() => {
		void search;
		void filter;
		page = 1;
	});

	function setFilter(next: Filter) {
		filter = next;
	}
</script>

<svelte:head>
	<title>Subscriptions · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader
		title="Subscriptions"
		description="From draft to closed — every contract and where it stands."
	>
		{#snippet actions()}
			<Button href="/subscriptions/new">
				<Icon name="plus" size={16} />
				New subscription
			</Button>
		{/snippet}
	</PageHeader>

	<div class="flex flex-wrap gap-1.5">
		<button
			type="button"
			class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition"
			class:bg-brand-600={filter === 'all'}
			class:text-white={filter === 'all'}
			class:bg-white={filter !== 'all'}
			class:text-slate-600={filter !== 'all'}
			class:border={filter !== 'all'}
			class:border-slate-200={filter !== 'all'}
			onclick={() => setFilter('all')}
		>
			All
			<span
				class="rounded-full px-1.5 text-[10px] {filter === 'all' ? 'bg-white/20' : 'bg-slate-100'}"
			>
				{db.data.subscriptions.length}
			</span>
		</button>
		{#each statuses as status (status)}
			<button
				type="button"
				class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition"
				class:bg-brand-600={filter === status}
				class:text-white={filter === status}
				class:bg-white={filter !== status}
				class:text-slate-600={filter !== status}
				class:border={filter !== status}
				class:border-slate-200={filter !== status}
				onclick={() => setFilter(status)}
			>
				{titleCase(status)}
				<span
					class="rounded-full px-1.5 text-[10px] {filter === status
						? 'bg-white/20'
						: 'bg-slate-100'}"
				>
					{counts[status]}
				</span>
			</button>
		{/each}
	</div>

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
		<div class="w-full sm:max-w-xs">
			<Input placeholder="Search number, customer or plan…" icon="search" bind:value={search} />
		</div>
		<p class="text-xs text-slate-400 sm:ml-auto">{rows.length} subscriptions</p>
	</div>

	<Table
		columns={[
			{ label: 'Subscription' },
			{ label: 'Customer' },
			{ label: 'Plan' },
			{ label: 'Status' },
			{ label: 'Term' },
			{ label: 'Next renewal' },
			{ label: 'Value', align: 'right' },
			{ label: '', align: 'right' }
		]}
		rowCount={paged.length}
		emptyTitle="No subscriptions found"
		emptyDescription="Try another filter, or create your first subscription."
		emptyIcon="repeat"
	>
		{#snippet emptyAction()}
			<Button size="sm" href="/subscriptions/new">New subscription</Button>
		{/snippet}

		{#each paged as row (row.subscription.id)}
			{@const days = daysUntil(row.subscription.endDate)}
			<tr class="transition hover:bg-slate-50">
				<td class="px-4 py-3">
					<a
						href={`/subscriptions/${row.subscription.id}`}
						class="font-medium text-slate-800 hover:text-brand-600"
					>
						{row.subscription.number}
					</a>
					<p class="text-xs text-slate-400">{row.subscription.lines.length} line(s)</p>
				</td>
				<td class="px-4 py-3">
					<div class="flex items-center gap-2">
						<Avatar name={row.customer?.company ?? 'Customer'} size="xs" />
						<div class="min-w-0">
							<p class="truncate text-slate-700">{row.customer?.company ?? '—'}</p>
							<p class="truncate text-xs text-slate-400">{row.customer?.name ?? ''}</p>
						</div>
					</div>
				</td>
				<td class="px-4 py-3">
					<p class="text-slate-700">{row.plan?.name ?? '—'}</p>
					<Badge tone="slate">{row.plan?.billingPeriod ?? '—'}</Badge>
				</td>
				<td class="px-4 py-3"><StatusBadge status={row.subscription.status} /></td>
				<td class="px-4 py-3 text-xs whitespace-nowrap text-slate-500">
					{formatDate(row.subscription.startDate)}<br />
					<span class="text-slate-400">to {formatDate(row.subscription.endDate)}</span>
				</td>
				<td class="px-4 py-3 text-xs whitespace-nowrap">
					{#if row.subscription.status === 'active'}
						<span
							class={days < 0 ? 'text-rose-600' : days < 30 ? 'text-amber-600' : 'text-slate-500'}
						>
							{relativeDays(row.subscription.endDate)}
						</span>
					{:else}
						<span class="text-slate-400">—</span>
					{/if}
				</td>
				<td class="px-4 py-3 text-right whitespace-nowrap">
					<p class="font-medium text-slate-700">{currency(subscriptionTotal(row.subscription))}</p>
					<p class="text-[11px] text-slate-400">{currency(row.value)}/mo</p>
				</td>
				<td class="px-4 py-3">
					<div class="flex justify-end">
						<Button
							variant="ghost"
							size="icon"
							title="Open subscription"
							href={`/subscriptions/${row.subscription.id}`}
						>
							<Icon name="arrow-right" size={15} />
						</Button>
					</div>
				</td>
			</tr>
		{/each}
	</Table>

	{#if rows.length > pageSize}
		<Pagination {page} {pageSize} total={rows.length} onpage={(next) => (page = next)} />
	{/if}
</div>
