<script lang="ts">
	import { cn } from '#lib/utils/format';

	interface Option {
		value: string;
		label: string;
	}

	interface Props {
		label?: string;
		hint?: string;
		error?: string;
		value?: string | null;
		options: Option[];
		placeholder?: string;
		required?: boolean;
		disabled?: boolean;
		class?: string;
		onchange?: (event: Event) => void;
	}

	let {
		label,
		hint,
		error,
		value = $bindable(''),
		options,
		placeholder = '',
		required = false,
		disabled = false,
		class: extra = '',
		onchange
	}: Props = $props();
</script>

<label class={cn('block', extra)}>
	{#if label}
		<span class="mb-1.5 flex items-center gap-1 text-xs font-medium text-slate-600">
			{label}
			{#if required}<span class="text-rose-500">*</span>{/if}
		</span>
	{/if}
	<select
		bind:value
		{required}
		{disabled}
		{onchange}
		class={cn(
			'w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition focus:ring-2 focus:outline-none disabled:bg-slate-50 disabled:text-slate-500',
			error
				? 'border-rose-300 focus:border-rose-400 focus:ring-rose-200'
				: 'border-slate-300 focus:border-brand-500 focus:ring-brand-500/20'
		)}
	>
		{#if placeholder}
			<option value="" disabled>{placeholder}</option>
		{/if}
		{#each options as option (option.value)}
			<option value={option.value}>{option.label}</option>
		{/each}
	</select>
	{#if error}
		<span class="mt-1 block text-xs text-rose-600">{error}</span>
	{:else if hint}
		<span class="mt-1 block text-xs text-slate-400">{hint}</span>
	{/if}
</label>
