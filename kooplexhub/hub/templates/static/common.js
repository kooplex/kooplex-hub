// my boolean converter
function B(x) {
  if (typeof x === 'boolean') {
    return x;
  }
  if (typeof x === 'string') {
    return Boolean(x == 'true') || Boolean(x == 'True');
  }
  console.log("fallback to unhandled type");
  return Boolean(x);
};

