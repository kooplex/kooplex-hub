# Environment lifecycle

start
  validate routes
  remove legacy direct Pod
  reconcile Service
  reconcile Deployment
  add/update proxy routes

stop
  remove proxy routes
  delete Deployment
  delete Service

restart
  reconcile current configuration
  add/update routes
  force Deployment rollout
