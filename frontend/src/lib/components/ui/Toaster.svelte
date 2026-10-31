<script lang="ts">
	import { toasts } from '#lib/stores/toasts.svelte';
	import Icon from './Icon.svelte';
	import { cn } from '#lib/utils/format';

	const styles = {
		success: 'border-emerald-200 bg-white text-emerald-700',
		error: 'border-rose-200 bg-white text-rose-700',
		info: 'border-sky-200 bg-white text-sky-700'
	};

	const icons = {
		success: 'check-circle',
		error: 'exclamation',
		info: 'bell'
	};
</script>

<div class="pointer-events-none fixed right-4 bottom-4 z-[60] flex w-full max-w-sm flex-col gap-2">
	{#each toasts.items as toast (toast.id)}
		<div
			class={cn(
				'pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg shadow-slate-900/5',
				styles[toast.type]
			)}
		>
			<Icon name={icons[toast.type]} size={18} class="mt-0.5 shrink-0" />
			<p class="flex-1 text-sm font-medium text-slate-700">{toast.message}</p>
			<button
				type="button"
				class="text-slate-400 transition hover:text-slate-600"
				aria-label="Dismiss notification"
				onclick={() => toasts.dismiss(toast.id)}
			>
				<Icon name="close" size={14} />
			</button>
		</div>
	{/each}
</div>
