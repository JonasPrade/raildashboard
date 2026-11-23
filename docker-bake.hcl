# The build part of `make test` (Makefile → test), as one `docker buildx bake` run.
# Always passed with `-f docker-bake.hcl`: without it bake also reads compose.yaml.
#
# Bake builds all targets in parallel and computes shared stages once (the
# backend `builder` stage feeds both `test` and `runtime`). Every target writes
# only to the build cache (`type=cacheonly`): the check is that the stages
# build and their tests pass, the images themselves are built and pushed by
# release.yml.
#
# CACHE_REF switches on a registry cache. CI sets it to the GHCR image prefix;
# PR runs and master runs then share one cache, so a merge commit whose tree the
# PR run already checked hits every layer and finishes in about a minute, and
# apt/pip/npm/Maven only run again when their inputs change. Local runs leave it
# empty and use the docker daemon's own cache.

variable "CACHE_REF" {
  default = ""
}

# Cache refs: <prefix>-<service>:pruefcache-<target>, next to the images of the
# same service. The runtime targets also read release.yml's `buildcache`.
function "cache_from" {
  params = [service, name, extra]
  result = CACHE_REF == "" ? [] : concat(
    ["type=registry,ref=${CACHE_REF}-${service}:pruefcache-${name}"],
    extra ? ["type=registry,ref=${CACHE_REF}-${service}:buildcache"] : []
  )
}

# ignore-error: a run without write access to the registry still checks.
function "cache_to" {
  params = [service, name]
  result = CACHE_REF == "" ? [] : ["type=registry,ref=${CACHE_REF}-${service}:pruefcache-${name},mode=max,ignore-error=true"]
}

group "pruefung" {
  targets = ["backend-test", "frontend-check", "backend-runtime", "frontend-runtime", "db", "graphhopper-test"]
}

target "_pruefung" {
  output = ["type=cacheonly"]
}

# pytest (without tests/db_related_tests)
target "backend-test" {
  inherits   = ["_pruefung"]
  context    = "apps/backend"
  target     = "test"
  contexts   = { skills = ".claude/skills" }
  cache-from = cache_from("backend", "test", false)
  cache-to   = cache_to("backend", "test")
}

# tsc --noEmit, eslint, Vitest
target "frontend-check" {
  inherits   = ["_pruefung"]
  context    = "apps/frontend"
  target     = "check"
  cache-from = cache_from("frontend", "check", false)
  cache-to   = cache_to("frontend", "check")
}

target "backend-runtime" {
  inherits   = ["_pruefung"]
  context    = "apps/backend"
  target     = "runtime"
  contexts   = { skills = ".claude/skills" }
  cache-from = cache_from("backend", "runtime", true)
  cache-to   = cache_to("backend", "runtime")
}

target "frontend-runtime" {
  inherits   = ["_pruefung"]
  context    = "apps/frontend"
  target     = "runtime"
  cache-from = cache_from("frontend", "runtime", true)
  cache-to   = cache_to("frontend", "runtime")
}

target "db" {
  inherits   = ["_pruefung"]
  context    = "docker/db"
  cache-from = cache_from("db", "runtime", true)
  cache-to   = cache_to("db", "runtime")
}

# Unit tests of the OpenRailRouting extension and the smoke test (since #364)
target "graphhopper-test" {
  inherits   = ["_pruefung"]
  context    = "docker/graphhopper"
  target     = "test"
  cache-from = cache_from("graphhopper", "test", false)
  cache-to   = cache_to("graphhopper", "test")
}
