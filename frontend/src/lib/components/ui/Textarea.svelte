<script lang="ts">
	import { cn } from '#lib/utils/format';

	interface Props {
		label?: string;
		hint?: string;
		error?: string;
		value?: string;
		placeholder?: string;
		rows?: number;
		required?: boolean;
		disabled?: boolean;
		class?: string;
	}

	let {
		label,
		hint,
		error,
		value = $bindable(''),
		placeholder,
		rows = 3,
		required = false,
		disabled = false,
		class: extra = ''
	}: Props = $props();
</script>

<label class={cn('block', extra)}>
	{#if label}
		<span class="mb-1.5 flex items-center gap-1 text-xs font-medium text-slate-600">
			{label}
			{#if required}<span class="text-rose-500">*</span>{/if}
		</span>
	{/if}
	<textarea
		{rows}
		{placeholder}
		{required}
		{disabled}
		bind:value
		class={cn(
			'w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition placeholder:text-slate-400 focus:ring-2 focus:outline-none disabled:bg-slate-50 disabled:text-slate-500',
			error
				? 'border-rose-300 focus:border-rose-400 focus:ring-rose-200'
				: 'border-slate-300 focus:border-brand-500 focus:ring-brand-500/20'
		)}></textarea>
	{#if error}
		<span class="mt-1 block text-xs text-rose-600">{error}</span>
	{:else if hint}
		<span class="mt-1 block text-xs text-slate-400">{hint}</span>
	{/if}
</label>
