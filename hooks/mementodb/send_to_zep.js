/**
 * MementoDB Trigger Script: Send new entries to Zep memory.
 *
 * Setup in MementoDB:
 *   Event:  "Creating an entry"
 *   Phase:  "After saving the entry"
 *
 * Configuration: set ZEP_API_KEY and ZEP_USER_ID in the constants below.
 */

var ZEP_API_KEY = "YOUR_ZEP_API_KEY";
var ZEP_USER_ID = "YOUR_ZEP_USER_ID";
var ZEP_API_URL = "https://api.getzep.com/api/v2/graph";

var e = entry();
var fieldNames = lib().fields();
var fields = {};
for (var i = 0; i < fieldNames.length; i++) {
  fields[fieldNames[i]] = e.field(fieldNames[i]);
}

var data = JSON.stringify({
  library: lib().title,
  entry_id: e.id,
  title: e.title,
  description: e.description,
  author: e.author,
  created: e.creationTime,
  fields: fields,
});

var payload = JSON.stringify({
  data: data,
  type: "json",
  user_id: ZEP_USER_ID,
});

var client = http();
client.headers({
  "Content-Type": "application/json",
  "Authorization": ("Api-Key " + ZEP_API_KEY).toString(),
});

var result = client.post(ZEP_API_URL.toString(), payload.toString());

if (result.code >= 200 && result.code < 300) {
  message("memmed");
} else {
  message("Zep error (HTTP " + result.code + ")");
  log(
    "Zep: failed to send entry '" + e.title + "' (HTTP " + result.code + "): " +
      result.body,
  );
}
