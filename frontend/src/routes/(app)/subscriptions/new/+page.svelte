<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { db } from '#lib/data/store.svelte';
	import { createSubscription } from '#lib/data/operations';
	import { planById, roundMoney, taxRate } from '#lib/data/selectors';
	import type { SubscriptionLine, SubscriptionStatus } from '#lib/data/types';
	import Button from '#lib/components/ui/Button.svelte';
	import Card from '#lib/components/ui/Card.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import Input from '#lib/components/ui/Input.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import Select from '#lib/components/ui/Select.svelte';
	import Textarea from '#lib/components/ui/Textarea.svelte';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { addPeriod, formatDate, paymentTermsLabel, todayISO } from '#lib/utils/date';
	import { currency } from '#lib/utils/format';
	import { uid } from '#lib/utils/validation';

	const customerFromUrl = page.url.searchParams.get('customer') ?? '';

	let customerId = $state(customerFromUrl);
	let planId = $state('');
	let startDate = $state(todayISO());
	let endDate = $state(addPeriod(todayISO(), 'monthly'));
	let paymentTerms = $state('net_30');
	let quantity = $state(1);
	let notes = $state('');
	let formError = $state('');
	let saving = $state<'draft' | 'quotation' | null>(null);

	let plan = $derived(planById(db.data, planId || null));

	let customerOptions = $derived(
		db.data.customers
			.map((customer) => ({
				value: customer.id,
				label: `${customer.company} — ${customer.name}`
			}))
			.sort((a, b) => a.label.localeCompare(b.label))
	);
	let planOptions = $derived(
		db.data.plans
			.filter((item) => item.active)
			.map((item) => ({
				value: item.id,
				label: `${item.name} · ${currency(item.price)}/${item.billingPeriod}`
			}))
	);
	let termsOptions = $derived(
		['due_on_receipt', 'net_15', 'net_30', 'net_45', 'net_60'].map((value) => ({
			value,
			label: paymentTermsLabel(value)
		}))
	);

	let defaultTaxId = db.data.taxes.find((tax) => tax.active)?.id ?? '';
	let subtotal = $derived(plan ? roundMoney(plan.price * quantity) : 0);
	let taxTotal = $derived(roundMoney(subtotal * (taxRate(db.data, defaultTaxId) / 100)));
	let total = $derived(roundMoney(subtotal + taxTotal));

	$effect(() => {
		const selected = planById(db.data, planId || null);
		if (!selected) return;
		endDate = addPeriod(startDate, selected.billingPeriod);
		quantity = selected.minQuantity;
	});

	function validate(): string | null {
		if (!customerId) return 'Choose a customer.';
		if (!plan) return 'Choose a plan.';
		if (!startDate || !endDate) return 'Set the subscription start and end dates.';
		if (endDate <= startDate) return 'The end date must be after the start date.';
		if (Number(quantity) < plan.minQuantity) {
			return `${plan.name} requires at least ${plan.minQuantity} unit(s).`;
		}
		return null;
	}

	async function submit(status: Extract<SubscriptionStatus, 'draft' | 'quotation'>) {
		formError = validate() ?? '';
		if (formError || !plan) return;

		saving = status;
		const line: SubscriptionLine = {
			id: uid('subLine'),
			productId: plan.productId,
			variantId: null,
			quantity: Number(quantity) || plan.minQuantity,
			unitPrice: plan.price,
			taxId: defaultTaxId
		};

		try {
			const subscription = await createSubscription({
				customerId,
				planId,
				startDate,
				endDate,
				paymentTerms,
				status,
				discountId: null,
				notes,
				lines: [line]
			});
			toasts.success(`${subscription.number} saved as ${status}.`);
			await goto(`/subscriptions/${subscription.id}`);
		} catch (error) {
			formError = error instanceof Error ? error.message : 'Could not create the subscription.';
		} finally {
			saving = null;
		}
	}
</script>

<svelte:head>
	<title>New subscription · Brightloop</title>
</svelte:head>

<div class="space-y-6">
	<PageHeader
		title="New subscription"
		description="Choose a customer and plan, then set the billing period."
		backHref="/subscriptions"
		backLabel="Subscriptions"
	/>

	{#if formError}
		<p class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
			{formError}
		</p>
	{/if}

	<div class="grid gap-6 xl:grid-cols-3">
		<div class="space-y-6 xl:col-span-2">
			<Card>
				<h2 class="text-sm font-semibold text-slate-900">Customer &amp; plan</h2>
				<p class="text-xs text-slate-400">The plan sets the price and billing cadence.</p>

				<div class="mt-4 grid gap-4 sm:grid-cols-2">
					<Select
						label="Customer"
						placeholder="Choose a customer"
						bind:value={customerId}
						options={customerOptions}
					/>
					<Select
						label="Plan"
						placeholder="Choose a plan"
						bind:value={planId}
						options={planOptions}
					/>
					<Input label="Start date" type="date" bind:value={startDate} />
					<Input label="End date" type="date" bind:value={endDate} />
					<Input label="Quantity" type="number" min={1} bind:value={quantity} />
					<Select label="Payment terms" bind:value={paymentTerms} options={termsOptions} />
				</div>
			</Card>

			<Card>
				<h2 class="text-sm font-semibold text-slate-900">Notes</h2>
				<p class="text-xs text-slate-400">Optional internal notes for this subscription.</p>
				<div class="mt-4">
					<Textarea
						label="Internal notes"
						placeholder="Anything the team should know?"
						bind:value={notes}
					/>
				</div>
			</Card>
		</div>

		<div class="xl:col-span-1">
			<Card class="xl:sticky xl:top-20">
				<h2 class="text-sm font-semibold text-slate-900">Summary</h2>

				<dl class="mt-4 space-y-2 text-sm">
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Customer</dt>
						<dd class="truncate text-right font-medium text-slate-700">
							{db.data.customers.find((customer) => customer.id === customerId)?.company ?? '—'}
						</dd>
					</div>
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Plan</dt>
						<dd class="text-right font-medium text-slate-700">{plan?.name ?? '—'}</dd>
					</div>
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Period</dt>
						<dd class="text-right text-slate-600">
							{startDate ? formatDate(startDate) : '—'} → {endDate ? formatDate(endDate) : '—'}
						</dd>
					</div>
					<div class="flex items-center justify-between gap-2">
						<dt class="text-slate-400">Payment terms</dt>
						<dd class="text-right text-slate-600">{paymentTermsLabel(paymentTerms)}</dd>
					</div>
				</dl>

				<div class="mt-4 space-y-2 border-t border-slate-100 pt-4 text-sm">
					<div class="flex items-center justify-between">
						<span class="text-slate-500">Subtotal</span>
						<span class="font-medium text-slate-700">{currency(subtotal)}</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-slate-500">Tax</span>
						<span class="font-medium text-slate-700">{currency(taxTotal)}</span>
					</div>
					<div class="flex items-center justify-between border-t border-slate-100 pt-2 text-base">
						<span class="font-semibold text-slate-900">Total</span>
						<span class="font-semibold text-slate-900">{currency(total)}</span>
					</div>
					<p class="text-[11px] text-slate-400">
						{quantity} unit(s) · billed {plan?.billingPeriod ?? 'monthly'}
					</p>
				</div>

				<div class="mt-5 space-y-2">
					<Button class="w-full" onclick={() => submit('quotation')} disabled={saving !== null}>
						<Icon name="file-text" size={16} />
						{saving === 'quotation' ? 'Creating…' : 'Create quotation'}
					</Button>
					<Button
						variant="outline"
						class="w-full"
						onclick={() => submit('draft')}
						disabled={saving !== null}
					>
						{saving === 'draft' ? 'Saving…' : 'Save as draft'}
					</Button>
				</div>
			</Card>
		</div>
	</div>
</div>
