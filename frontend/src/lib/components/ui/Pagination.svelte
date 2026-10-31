<script lang="ts">
	import { formatNumber } from '#lib/utils/format';
	import Icon from './Icon.svelte';

	interface Props {
		page: number;
		pageSize: number;
		total: number;
		onpage: (page: number) => void;
	}

	let { page, pageSize, total, onpage }: Props = $props();

	let pages = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let from = $derived(total === 0 ? 0 : (page - 1) * pageSize + 1);
	let to = $derived(Math.min(page * pageSize, total));

	let visible = $derived.by(() => {
		const list: number[] = [];
		const start = Math.max(1, Math.min(page - 1, pages - 2));
		const end = Math.min(pages, start + 2);
		for (let index = start; index <= end; index++) list.push(index);
		return list;
	});
</script>

<div class="flex flex-col items-center justify-between gap-3 sm:flex-row">
	<p class="text-xs text-slate-500">
		Showing <span class="font-semibold text-slate-700">{formatNumber(from)}–{formatNumber(to)}</span
		>
		of <span class="font-semibold text-slate-700">{formatNumber(total)}</span>
	</p>

	<div class="flex items-center gap-1">
		<button
			type="button"
			class="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
			disabled={page <= 1}
			aria-label="Previous page"
			onclick={() => onpage(page - 1)}
		>
			<Icon name="chevron-left" size={16} />
		</button>

		{#each visible as number (number)}
			<button
				type="button"
				class="flex h-8 min-w-8 items-center justify-center rounded-lg px-2 text-xs font-medium transition"
				class:bg-brand-600={number === page}
				class:text-white={number === page}
				class:text-slate-600={number !== page}
				class:hover:bg-slate-100={number !== page}
				onclick={() => onpage(number)}
			>
				{number}
			</button>
		{/each}

		<button
			type="button"
			class="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
			disabled={page >= pages}
			aria-label="Next page"
			onclick={() => onpage(page + 1)}
		>
			<Icon name="chevron-right" size={16} />
		</button>
	</div>
</div>
