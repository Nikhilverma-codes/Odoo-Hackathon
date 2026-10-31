<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Column } from '#lib/data/types';
	import { cn } from '#lib/utils/format';
	import EmptyState from './EmptyState.svelte';

	interface Props {
		columns: Column[];
		rowCount: number;
		loading?: boolean;
		emptyTitle?: string;
		emptyDescription?: string;
		emptyIcon?: string;
		emptyAction?: Snippet;
		children: Snippet;
		footer?: Snippet;
		class?: string;
	}

	let {
		columns,
		rowCount,
		loading = false,
		emptyTitle = 'Nothing here yet',
		emptyDescription = 'Try adjusting your filters or create a new record.',
		emptyIcon = 'box',
		emptyAction,
		children,
		footer,
		class: extra = ''
	}: Props = $props();

	const alignClass: Record<string, string> = {
		left: 'text-left',
		right: 'text-right',
		center: 'text-center'
	};
</script>

<div
	class={cn(
		'overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm shadow-slate-900/[0.03]',
		extra
	)}
>
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-slate-200 text-sm">
			<thead class="bg-slate-50">
				<tr>
					{#each columns as column (column.label)}
						<th
							scope="col"
							style={column.width ? `width:${column.width}` : undefined}
							class={cn(
								'px-4 py-3 text-[11px] font-semibold tracking-wide whitespace-nowrap text-slate-500 uppercase',
								alignClass[column.align ?? 'left']
							)}
						>
							{column.label}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#if loading}
					{#each Array(5) as _, index (index)}
						<tr>
							{#each columns as column (column.label)}
								<td class="px-4 py-4">
									<div class="h-4 animate-pulse rounded bg-slate-100"></div>
								</td>
							{/each}
						</tr>
					{/each}
				{:else if rowCount === 0}
					<tr>
						<td colspan={columns.length}>
							<EmptyState icon={emptyIcon} title={emptyTitle} description={emptyDescription}>
								{#snippet action()}
									{#if emptyAction}{@render emptyAction()}{/if}
								{/snippet}
							</EmptyState>
						</td>
					</tr>
				{:else}
					{@render children()}
				{/if}
			</tbody>
		</table>
	</div>

	{#if footer}
		<div class="border-t border-slate-100 bg-white px-4 py-3">
			{@render footer()}
		</div>
	{/if}
</div>
