# Google Cloud for a retired programmer

*A practical guide to the trial, useful experiments and manageable costs.*

Prepared 3 November 2026. Offers and console screens can change; check the linked official references. Your own billing status must be checked separately.

## What is Google Cloud?

Google Cloud lets you run programs and keep data on Google's computers. You can rent a Linux virtual machine, deploy an application, query large datasets or call specialist APIs. You manage services through a browser, command-line tools or your programs.

A **project** groups related services and settings. A **resource** is something you create, such as a virtual machine. A **billing account** pays for billable project resources. A **quota** limits usage; it is not a price or spending limit. Start with one small project.

## What does the free trial provide?

The standard trial currently offers **US$300 of credit for 90 days**, ending when the credit or time runs out. Google says you will not be charged during the Free Trial and will not be moved to paid billing unless you manually upgrade. Some services are restricted during the trial. See the [trial FAQ](https://cloud.google.com/signup-faqs).

If you upgrade, unused credit remains available until its original expiration date. Usage outside the credit's coverage or beyond the remaining credit and free allowances can then be charged. If you do not upgrade, trial resources stop when the trial ends. Google describes a 30-day recovery grace period, followed by deletion; keep local copies of anything important. See the [free-program terms and limits](https://docs.cloud.google.com/free/docs/free-cloud-features).

The ongoing **Free Tier** is a separate set of product-specific allowances. It does not make every service free, and a paid account can incur charges beyond those allowances. There is no need to spend the whole trial credit to get value from the experience.

## Why did this appear during the YouTube setup?

Google uses the Cloud console to register applications, enable the YouTube Data API and create authorization credentials. That can put a trial offer in your path. Registering an API project and renting cloud computing are separate activities. The [YouTube API overview](https://developers.google.com/youtube/data/getting-started) explains the project-and-credentials setup.

Your existing YouTube/GitHub discovery application runs on your WSL PC. Its local Python programs, SQLite database and private review dashboard do not need a cloud server. Your public static catalog already uses GitHub Pages. Exploring Google Cloud would be an additional experiment, not a prerequisite for continuing that work.

## Is it worthwhile for you?

It could be, especially for investigating mathematics, physics, computing and data through a concrete problem. The benefits include a different computing environment, occasional extra CPU or memory, and a way to share a dynamic demonstration.

Permissions, deployment and billing take time to learn. Choose a question you care about, keep the experiment small and judge whether the platform helped. As a retired programmer, you can judge it by enjoyment and useful results. Continuing with local tools is a reasonable outcome.

<!-- PDF page break -->

# Three experiments to try

## 1. Explore a dataset with BigQuery

BigQuery queries large tables using SQL without a database server to manage. Ask a focused question of a public dataset: how does a quantity vary by location, season or category? Export a small result and plot it locally with Python.

The [BigQuery sandbox](https://docs.cloud.google.com/bigquery/docs/sandbox) works without a credit card or billing account. It has usage and feature limits; sandbox tables expire after 60 days. Start with its public-dataset tutorial and save your SQL and results locally. This is my first choice for data exploration, and requires no trial credit.

## 2. Run a numerical experiment on Compute Engine

A Compute Engine virtual machine is a remote computer you configure for a task. Try a Monte Carlo calculation, small PDE solver or parameter sweep. Compare local and remote runtime, memory use and numerical results. A larger machine is not automatically faster.

Start with an ordinary CPU machine and Google's [instance creation guide](https://docs.cloud.google.com/compute/docs/instances/create-start-instance). Check the selected machine's cost estimate before creating it. When finished, download results and remove experiment resources you no longer need. Consult the [stop/restart guide](https://docs.cloud.google.com/compute/docs/instances/stop-start-instance) rather than assuming a closed browser tab stops the machine.

## 3. Share a small application with Cloud Run

[Cloud Run](https://cloud.google.com/run) runs applications and jobs without requiring you to administer a full server. A small Python demonstration could let someone vary a resonance parameter, explore a mathematical model or compare signal-processing methods. Start with synthetic or public data.

Cloud Run supports source deployment and scaling down to zero. Builds, image storage and associated services have separate pricing; check the [pricing page](https://cloud.google.com/run/pricing). Keep your personal research database and review decisions local while learning deployment.

## A first afternoon: one question, one result

1. **Check your account.** Open [Cloud Billing](https://console.cloud.google.com/billing), select the billing account and check Free trial versus Paid account. Note remaining credit and the expiration date.
2. **Choose one experiment.** Try the BigQuery tutorial or a small CPU calculation. A separate project makes new resources easier to identify.
3. **Define success.** Aim for one query and graph, a reproducible timing comparison, or a working demonstration. Follow the official quickstart and record changes.
4. **Finish deliberately.** Save code and results locally. Review resources and costs, remove what you no longer need, then decide whether to continue.

## Keep the financial distinction clear

Remaining trial credit is not cash to withdraw. Upgrading enables paid usage; it is a separate decision from merely experimenting. On a paid account, an ordinary alerts-only budget sends notifications and does **not** automatically stop spending. Google also documents spend-cap budgets for supported services; check their coverage before relying on them. See [budgets and alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets).

Aim to understand one useful tool and answer one interesting question before considering a larger cloud project.
