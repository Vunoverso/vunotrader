#ifndef VUNO_BRIDGE_JSON_MQH
#define VUNO_BRIDGE_JSON_MQH

string TrimValue(string value)
{
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
}


string JsonEscape(string text)
{
   string result = text;
   StringReplace(result, "\\", "\\\\");
   StringReplace(result, "\"", "\\\"");
   return result;
}


string ExtractJsonRawValue(string payload, string key)
{
   string pattern = "\"" + key + "\":";
   int pos = StringFind(payload, pattern);
   if(pos < 0)
      return "";

   int start = pos + StringLen(pattern);
   int length = StringLen(payload);

   while(start < length)
   {
      ushort c = StringGetCharacter(payload, start);
      if(c == ' ' || c == '\t' || c == '\r' || c == '\n')
      {
         start++;
         continue;
      }
      break;
   }

   if(start >= length)
      return "";

   if(StringGetCharacter(payload, start) == '"')
   {
      int endQuoted = start + 1;
      while(endQuoted < length)
      {
         if(StringGetCharacter(payload, endQuoted) == '"' && StringGetCharacter(payload, endQuoted - 1) != '\\')
            break;
         endQuoted++;
      }
      return StringSubstr(payload, start + 1, endQuoted - start - 1);
   }

   int end = start;
   while(end < length)
   {
      ushort c = StringGetCharacter(payload, end);
      if(c == ',' || c == '}' || c == '\r' || c == '\n')
         break;
      end++;
   }

   return TrimValue(StringSubstr(payload, start, end - start));
}


string JsonGetString(string payload, string key)
{
   return ExtractJsonRawValue(payload, key);
}


double JsonGetDouble(string payload, string key, double fallback)
{
   string value = ExtractJsonRawValue(payload, key);
   if(value == "")
      return fallback;
   return StringToDouble(value);
}


long JsonGetLong(string payload, string key, long fallback)
{
   string value = ExtractJsonRawValue(payload, key);
   if(value == "")
      return fallback;
   return (long)StringToInteger(value);
}

#endif