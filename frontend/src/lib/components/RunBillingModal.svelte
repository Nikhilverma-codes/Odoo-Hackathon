<script lang="ts">
	import { goto } from '$app/navigation';
	import { runBilling, type BillingRunResult } from '#lib/data/operations';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { addDays, formatDate, todayISO } from '#lib/utils/date';
	import Button from './ui/Button.svelte';
	import Icon from './ui/Icon.svelte';
	import Input from './ui/Input.svelte';
	import Modal from './ui/Modal.svelte';
	import Toggle from './ui/Toggle.svelte';

	interface Props {
		open?: boolean;
		onclose: () => void;
	}

	let { open = false, onclose }: Props = $props();

	let asOf = $state(todayISO());
	let autoConfirm = $state(true);
	let preview = $state<BillingRunResult | null>(null);
	let result = $state<BillingRunResult | null>(null);
	let busy = $state<'preview' | 'run' | null>(null);
	let error = $state('');

	let previewPeriods = $derived(preview?.invoiceNumbers.length ?? 0);

	$effect(() => {
		if (open) {
			asOf = todayISO();
			autoConfirm = true;
			preview = null;
			result = null;
			busy = null;
			error = '';
		}
	});

	function setPreset(days: number) {
		asOf = days === 0 ? todayISO() : addDays(todayISO(), days);
		preview = null;
		result = null;
		error = '';
	}

	async function previewRun() {
		error = '';
		preview = null;
		busy = 'preview';
		const response = await runBilling({ asOf, autoConfirm, dryRun: true });
		busy = null;
		if (!response.ok) {
			error = response.error;
			return;
		}
		preview = response.result;
	}

	async function submit() {
		error = '';
		busy = 'run';
		const response = await runBilling({ asOf, autoConfirm });
		busy = null;
		if (!response.ok) {
			error = response.error;
			return;
		}
		result = response.result;
		preview = null;
		toasts.success(
			result.invoiced === 0
				? 'Billing run complete. Nothing was due.'
				: `${result.invoiced} invoice(s) ${autoConfirm ? 'issued' : 'drafted'}.`
		);
	}
</script>

<Modal
	{open}
	title="Run billing"
	description="Bill every active subscription that is due on or before the selected date."
	{onclose}
>
	{#if result}
		<div class="space-y-5">
			<div
				class="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3"
			>
				<Icon name="check-circle" size={20} class="mt-0.5 shrink-0 text-emerald-600" />
				<div>
					<p class="text-sm font-semibold text-emerald-800">
						{result.invoiced === 0
							? 'Nothing was due'
							: `${result.invoiced} invoice(s) ${autoConfirm ? 'issued' : 'saved as drafts'}`}
					</p>
					<p class="mt-0.5 text-xs text-emerald-700">
						Processed through {formatDate(result.asOf)}. Re-running is safe: each billing period is
						only invoiced once.
					</p>
				</div>
			</div>

			<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
				{#each [{ label: 'Scanned', value: result.scanned }, { label: 'Invoiced', value: result.invoiced }, { label: 'Closed', value: result.closed }, { label: 'Skipped', value: result.skipped }] as item (item.label)}
					<div class="rounded-xl border border-slate-200 bg-white px-3 py-2.5">
						<p class="text-[11px] tracking-wide text-slate-400 uppercase">{item.label}</p>
						<p class="mt-0.5 text-lg font-semibold text-slate-800">{item.value}</p>
					</div>
				{/each}
			</div>

			{#if result.invoiceNumbers.length > 0}
				<div>
					<p class="mb-2 text-xs font-medium text-slate-600">Generated invoices</p>
					<div class="flex flex-wrap gap-1.5">
						{#each result.invoiceNumbers as number (number)}
							<span
								class="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-600"
							>
								{number}
							</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if result.errors.length > 0}
				<div
					class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700"
				>
					{#each result.errors as message (message)}
						<p>{message}</p>
					{/each}
				</div>
			{/if}
		</div>
	{:else}
		<div class="space-y-5">
			{#if error}
				<p class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
					{error}
				</p>
			{/if}

			<div>
				<Input
					label="Bill through"
					type="date"
					bind:value={asOf}
					hint="Use a future date to bill the next cycle."
				/>
				<div class="mt-2 flex flex-wrap gap-1.5">
					<Button variant="ghost" size="sm" onclick={() => setPreset(0)}>Today</Button>
					<Button variant="ghost" size="sm" onclick={() => setPreset(30)}>Next 30 days</Button>
					<Button variant="ghost" size="sm" onclick={() => setPreset(90)}>Next 90 days</Button>
				</div>
			</div>

			<Toggle
				label="Issue invoices immediately"
				description="Turn this off to create the invoices as drafts for review."
				bind:checked={autoConfirm}
			/>

			{#if preview}
				<div class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
					<p class="text-sm font-semibold text-slate-800">
						{preview.scanned === 0
							? 'No subscriptions are due for this date'
							: `${preview.scanned} subscription(s) due`}
					</p>
					{#if preview.scanned > 0}
						<p class="mt-1 text-xs text-slate-500">
							{previewPeriods} billing period(s) ready to invoice. Nothing has been written yet.
						</p>
					{/if}
					{#if preview.errors.length > 0}
						<p class="mt-1 text-xs text-amber-700">{preview.errors.join(' ')}</p>
					{/if}
				</div>
			{/if}

			<p class="rounded-lg bg-brand-50 px-3 py-2 text-xs leading-relaxed text-brand-800">
				Billing is idempotent. The selected date moves each subscription's billing cursor forward,
				so the same period can never be invoiced twice.
			</p>
		</div>
	{/if}

	{#snippet footer()}
		{#if result}
			<Button variant="outline" onclick={onclose}>Done</Button>
			<Button
				onclick={() => {
					onclose();
					goto('/invoices');
				}}
			>
				View invoices
				<Icon name="arrow-right" size={15} />
			</Button>
		{:else}
			<Button variant="outline" onclick={onclose} disabled={busy !== null}>Cancel</Button>
			<Button variant="outline" onclick={previewRun} disabled={busy !== null || !asOf}>
				{busy === 'preview' ? 'Checking...' : 'Preview'}
			</Button>
			<Button onclick={submit} disabled={busy !== null || !asOf}>
				{busy === 'run' ? 'Running...' : 'Run billing'}
			</Button>
		{/if}
	{/snippet}
</Modal>
