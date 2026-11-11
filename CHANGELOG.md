# Changelog

## 0.1.0 (2026-11-11)


### ⚠ BREAKING CHANGES

* environment variables, headers and resource names are renamed.

### Features

* complete Kionga platform foundation ([8500c5e](https://github.com/kiongahq/workspace/commit/8500c5eb9ea75d49dd9439884f3b7a15c79eba3e))
* **console:** add metadata drilldowns and mounted notebook storage ([11b221c](https://github.com/kiongahq/workspace/commit/11b221c34d3c2d50c35eb7dd1640ceb87d2c8e77))
* expose project objects and feature views in Langflow ([3b846e7](https://github.com/kiongahq/workspace/commit/3b846e75ce7a3c414d78d535c69a24da5678fc76))
* integrate Hugging Face and secure project workspace workflows ([ddb3762](https://github.com/kiongahq/workspace/commit/ddb3762df1a95987b479ed9b63ba5e78d373c703))
* **operator:** reconcile provisioned user workspaces ([39d328f](https://github.com/kiongahq/workspace/commit/39d328fb830362d7d41059164be33d26effcaa1c))
* package Langflow canvas and scoped Kionga components ([614074f](https://github.com/kiongahq/workspace/commit/614074f280943645122afba6672797fb3160bb64))
* **release:** add reviewed versions and consistent publication ([bce3670](https://github.com/kiongahq/workspace/commit/bce3670dd00dc94d311882db9514cdc02128cc2d))
* **release:** standardize versions, changelogs and publication ([b29e32a](https://github.com/kiongahq/workspace/commit/b29e32aa2d04a1a3ab20f25bbf179a1640095253))
* rename mlaiops to kionga ([#52](https://github.com/kiongahq/workspace/issues/52)) ([75b1295](https://github.com/kiongahq/workspace/commit/75b1295dea23772f51ccb94c1f4dbf0e2c0006b9))
* **workbench:** Jupyter dev workbench + service connection guide ([2bbdfe3](https://github.com/kiongahq/workspace/commit/2bbdfe3c976ae67a48c72261b194736878cfebc7))
* **workflows:** ship Git-native function builder ([36f0616](https://github.com/kiongahq/workspace/commit/36f0616feb7f366b7a55b95593090a83d02693b0))
* **workspace:** add AI scaffolding and shared browser IDE ([4b793da](https://github.com/kiongahq/workspace/commit/4b793dac27fca4b67ed22308a8b77b9b347f31a9))
* **workspace:** persist user tools and proxy workspace identity ([e389a55](https://github.com/kiongahq/workspace/commit/e389a55b6736afd0496e3367da8c669e404cbe54))
* **workspace:** sidecar scaffold-jobs endpoint with argv allowlist, scrubbed env and token; expose it in Jupyter via jupyter-server-proxy ([4a7ac82](https://github.com/kiongahq/workspace/commit/4a7ac823e433f1493da17cb29431a2d43f837777))


### Fixes

* document Langflow component loopback request boundary ([c410e79](https://github.com/kiongahq/workspace/commit/c410e7967de16b4976c5f232cb54c866d6c358d2))
* **jupyter:** build the workbench image on amd64 (Node arch mapping) ([8993970](https://github.com/kiongahq/workspace/commit/899397036e9460a4f606325f0639e07e99d27195))
* **jupyter:** quickstart notebook names MLflow 3.16.1 and the live docs URL ([36b95e6](https://github.com/kiongahq/workspace/commit/36b95e62b1ea191279b6dbec152abb955d32621a))
* P1 workspace auth and storage isolation (Jupyter token, job token, scoped S3 mounts) ([#48](https://github.com/kiongahq/workspace/issues/48)) ([c423d59](https://github.com/kiongahq/workspace/commit/c423d5927ae88d70d97704b95f2a26e490575e06))
* **realtime:** survive Kafka REST poll timeouts. A transient ReadTimeout ([2bbdfe3](https://github.com/kiongahq/workspace/commit/2bbdfe3c976ae67a48c72261b194736878cfebc7))
* **release:** start unreleased components at version 0.1.0 ([34f66ba](https://github.com/kiongahq/workspace/commit/34f66bad587a43be095400000d76312f7a368b6d))
* **security:** align MLflow images on patched version 3.17.2 ([f9c69f1](https://github.com/kiongahq/workspace/commit/f9c69f11b40d75b675d0fe549f695d8e9f861775))
* **security:** Jupyter image on MLflow 3.16.1 ([01ac20f](https://github.com/kiongahq/workspace/commit/01ac20f5314c800f3ae0671c68f68245af90d9f0))
* **workspace:** make local IDE launch through current gateway ([08c8fff](https://github.com/kiongahq/workspace/commit/08c8fff212ea3c0109c8e5c35096680cb3f09aa4))


### Documentation

* product README, CONTRIBUTING and ARCHITECTURE ([7e8158b](https://github.com/kiongahq/workspace/commit/7e8158b0829b00a30b4b2f85a79a7c1c08a49f43))
* **release:** align contributor publication instructions ([cf8c215](https://github.com/kiongahq/workspace/commit/cf8c21558e2e37c91e4fdd676a8a36f0081d6d93))
* **security:** clarify sole-maintainer release review ([beb8862](https://github.com/kiongahq/workspace/commit/beb8862befc750034259fb4375fd429b6f675e11))
* **workbench:** the bundled object store is RustFS ([16a1ff7](https://github.com/kiongahq/workspace/commit/16a1ff7bb35a0b5ac4175cbedd462569a3d169b9))
* **workspace:** describe authenticated API sidecar ([bdf7a48](https://github.com/kiongahq/workspace/commit/bdf7a48df1125d60cf21bf8b08edaf82b39232c8))


### Build and dependencies

* use SDK v0.3.1 ([#53](https://github.com/kiongahq/workspace/issues/53)) ([0cbc943](https://github.com/kiongahq/workspace/commit/0cbc943c1f31629615fe07beecb8d40803615600))


### Automation

* add Build & Publish workflow (images to GHCR) ([c80261b](https://github.com/kiongahq/workspace/commit/c80261b1babd5e9a130b73edb858574f9e0dffd7))
* report Langflow health retry attempts ([da79df9](https://github.com/kiongahq/workspace/commit/da79df9dea884dc4809f8bbfb5a07275580c2aa5))


### Maintenance

* ignore local tooling and secret files ([eedf3ac](https://github.com/kiongahq/workspace/commit/eedf3acad98cfda4db052d8fd87168075fc3fbbe))
* license repository under MIT ([da1c18c](https://github.com/kiongahq/workspace/commit/da1c18cf8bad1ef5cda89b40af700918ce05ee65))
* **security:** record bandit review of three flagged sites ([30f5d34](https://github.com/kiongahq/workspace/commit/30f5d34ca8efd214a2490003c6402fb2bfcfff0b))
* standalone workspace repo: Jupyter bundles platform sources from releases or sibling checkouts, generated-project tests run for real, CI and image publishing ([8e13e70](https://github.com/kiongahq/workspace/commit/8e13e700a4db916b83e8120a4afd891acf8e6283))

## Changelog

Reviewed release pull requests add versioned changes here.
Existing tags and releases remain available in [GitHub](https://github.com/kiongahq/workspace/releases).
