<script lang="ts">
	import { cn } from '#lib/utils/format';

	interface Props {
		checked?: boolean;
		label?: string;
		description?: string;
		disabled?: boolean;
		class?: string;
	}

	let {
		checked = $bindable(false),
		label,
		description,
		disabled = false,
		class: extra = ''
	}: Props = $props();
</script>

<div class={cn('flex items-start justify-between gap-4', extra)}>
	{#if label}
		<div class="min-w-0">
			<p class="text-sm font-medium text-slate-700">{label}</p>
			{#if description}
				<p class="text-xs text-slate-400">{description}</p>
			{/if}
		</div>
	{/if}
	<button
		type="button"
		role="switch"
		aria-label={label ?? 'Toggle'}
		aria-checked={checked}
		{disabled}
		onclick={() => (checked = !checked)}
		class={cn(
			'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition focus-visible:ring-2 focus-visible:ring-brand-500/40 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
			checked ? 'bg-brand-600' : 'bg-slate-300'
		)}
	>
		<span
			class={cn(
				'inline-block h-4 w-4 transform rounded-full bg-white shadow transition',
				checked ? 'translate-x-6' : 'translate-x-1'
			)}
		></span>
	</button>
</div>
