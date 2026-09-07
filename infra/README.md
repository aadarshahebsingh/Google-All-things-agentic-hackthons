# Infra configs

## firestore/
Firestore uses native mode with the default database. Collections are created
on demand: startups, evidence, personas_meta, simulations, customers,
customers_meta, outreach, consents, interviews, hypotheses, market_fit,
research, strategy, hackathons, investors, events.
No index configuration is required for current queries (single-field equality).

## pubsub/
gcloud pubsub topics create founder-shortcut-jobs
gcloud pubsub subscriptions create founder-shortcut-jobs-sub \
  --topic founder-shortcut-jobs \
  --push-endpoint https://WORKER_URL/pubsub/push --push-auth

## cloud-run/
See docs/deployment.md for full deploy commands.
