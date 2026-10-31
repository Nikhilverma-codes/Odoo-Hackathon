<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '#lib/auth/auth.svelte';
	import { homeFor } from '#lib/auth/permissions';
	import BrandMark from '#lib/components/BrandMark.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	let highlights = [
		{
			icon: 'repeat',
			title: 'Subscriptions on autopilot',
			text: 'Renewals, pauses and plan changes without spreadsheets.'
		},
		{
			icon: 'receipt',
			title: 'Invoices without busywork',
			text: 'Generate an invoice from any subscription in one click.'
		},
		{
			icon: 'chart',
			title: 'Revenue you can trust',
			text: 'Recurring revenue, collections and overdue balances in one view.'
		}
	];

	$effect(() => {
		if (auth.isAuthenticated) goto(homeFor(auth.role), { replaceState: true });
	});
</script>

<div class="flex min-h-screen bg-white">
	<section
		class="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-950 via-brand-800 to-violet-800 p-12 text-white lg:flex"
	>
		<div
			class="pointer-events-none absolute -top-24 -right-24 h-96 w-96 rounded-full bg-white/10 blur-3xl"
		></div>
		<div
			class="pointer-events-none absolute bottom-0 left-0 h-80 w-80 translate-y-1/3 rounded-full bg-brand-400/20 blur-3xl"
		></div>

		<div class="relative">
			<BrandMark href="/login" compact />
			<p class="mt-16 max-w-md text-3xl leading-tight font-semibold tracking-tight">
				Run plans, subscriptions and recurring billing in one place.
			</p>
			<p class="mt-4 max-w-md text-sm leading-relaxed text-brand-100">
				Brightloop is the digital backbone for companies that earn their money every month — not
				just once.
			</p>

			<ul class="mt-10 space-y-5">
				{#each highlights as item (item.title)}
					<li class="flex items-start gap-3">
						<span
							class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/10 text-white ring-1 ring-white/15"
						>
							<Icon name={item.icon} size={17} />
						</span>
						<div>
							<p class="text-sm font-semibold">{item.title}</p>
							<p class="text-xs text-brand-200">{item.text}</p>
						</div>
					</li>
				{/each}
			</ul>
		</div>

		<div class="relative grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
			<div>
				<p class="text-2xl font-semibold">$48.2k</p>
				<p class="text-[11px] tracking-wide text-brand-300 uppercase">Monthly recurring</p>
			</div>
			<div>
				<p class="text-2xl font-semibold">142</p>
				<p class="text-[11px] tracking-wide text-brand-300 uppercase">Active subscriptions</p>
			</div>
			<div>
				<p class="text-2xl font-semibold">98.4%</p>
				<p class="text-[11px] tracking-wide text-brand-300 uppercase">On-time payments</p>
			</div>
		</div>
	</section>

	<section class="flex w-full flex-col lg:w-1/2">
		<div class="flex items-center justify-between border-b border-slate-100 px-6 py-5 lg:hidden">
			<BrandMark href="/login" />
		</div>
		<div class="flex flex-1 items-center justify-center px-5 py-10 sm:px-10">
			<div class="w-full max-w-md">
				{@render children()}
			</div>
		</div>
		<p class="px-6 pb-6 text-center text-[11px] text-slate-400">
			Brightloop Software · Demo workspace
		</p>
	</section>
</div>
