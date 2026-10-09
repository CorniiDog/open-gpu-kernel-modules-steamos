#!/usr/bin/env python3
"""Exercise the production connector detection body with isolated KMS adapters."""
from pathlib import Path
import subprocess
import tempfile
import sys
source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "kernel-open/nvidia-drm/nvidia-drm-connector.c"
source = source_path.read_text()
start = source.index("static enum drm_connector_status __nv_drm_connector_detect_internal(")
end = source.index("static void __nv_drm_connector_force", start)
body = source[start:end]
stubs = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#define NULL ((void *)0)
enum drm_connector_status { connector_status_disconnected, connector_status_connected };
struct drm_encoder { int encoder_type; };
struct nv_drm_encoder { struct drm_encoder base; };
struct drm_device { struct { int mutex; int dvi_i_subconnector_property; } mode_config; };
struct drm_connector { struct drm_device *dev; int base; };
struct nv_drm_connector { struct drm_connector base; void *edid; struct nv_drm_encoder *nv_detected_encoder; int type; void *modeset_permission_filep; };
struct NvKmsKapiDynamicDisplayParams { int unused; };
static struct nv_drm_encoder test_encoder;
static bool connected, allocation_failure;
static int edid_clear, revoked;
#define to_nv_connector(c) ((struct nv_drm_connector *)(c))
#define to_nv_encoder(e) ((struct nv_drm_encoder *)(e))
#define BUG_ON(x) assert(!(x))
#define WARN_ON(x) ((void)(x))
#define mutex_is_locked(x) (*(x))
#define NVKMS_CONNECTOR_TYPE_DVI_I 1
#define DRM_MODE_ENCODER_DAC 1
#define DRM_MODE_SUBCONNECTOR_DVIA 1
#define DRM_MODE_SUBCONNECTOR_DVID 2
#define nv_drm_connector_for_each_possible_encoder(c,e) for ((e)=&test_encoder.base; (e); (e)=NULL)
#define nv_drm_connector_for_each_possible_encoder_end
static void *nv_drm_calloc(int n, size_t size) { return allocation_failure ? NULL : calloc(n,size); }
static void nv_drm_free(void *p) { free(p); }
static bool __nv_drm_detect_encoder(struct NvKmsKapiDynamicDisplayParams *p, struct drm_connector *c, struct drm_encoder *e) { return connected; }
static void drm_object_property_set_value(void *o, int p, int v) {}
static void nv_drm_connector_update_edid_property(struct drm_connector *c, void *edid) { assert(edid == NULL); edid_clear++; }
static void nv_drm_connector_revoke_permissions(struct drm_device *d, struct nv_drm_connector *c) { revoked++; c->modeset_permission_filep=NULL; }
"""
checks = r"""
int main(void) {
 struct drm_device dev = { .mode_config.mutex = 1 };
 struct nv_drm_connector c = { .base.dev=&dev };
 connected=true;
 assert(__nv_drm_connector_detect_internal(&c.base)==connector_status_connected);
 assert(c.nv_detected_encoder==&test_encoder && edid_clear==0);
 c.edid=malloc(8); c.modeset_permission_filep=&dev;
 connected=false;
 assert(__nv_drm_connector_detect_internal(&c.base)==connector_status_disconnected);
 assert(c.nv_detected_encoder==NULL && c.edid==NULL && edid_clear==1 && revoked==1);
 connected=true;
 assert(__nv_drm_connector_detect_internal(&c.base)==connector_status_connected);
 assert(c.nv_detected_encoder==&test_encoder);
 allocation_failure=true;
 assert(__nv_drm_connector_detect_internal(&c.base)==connector_status_disconnected);
 assert(c.nv_detected_encoder==NULL && edid_clear==2);
 return 0;
}
"""
with tempfile.TemporaryDirectory(prefix="opemos-hotplug-test-") as tmp:
 c=Path(tmp)/"test.c"; exe=Path(tmp)/"test"
 c.write_text(stubs+body+checks)
 subprocess.run(["cc", "-std=c99", "-Werror=implicit-function-declaration", str(c), "-o", str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print("PASS: connect, disconnect, reconnect, allocation-failure state and permission cleanup")
