Rank of the first passage on a correct page (±1) among the 8 given to the model; ✗ = not found.

| Q | bm25_step3 | keyword_stem | dense_bge_m3 | hybrid | turath_find |
|---|---|---|---|---|---|
| Q01 ما حكم الماء الآجن، وهو المتغير بطول مكثه؟ | 1 | 1 | 1 | 1 | ✗ |
| Q02 كم مقدار القلتين بالرطل العراقي؟ | 1 | 1 | 1 | 1 | ✗ |
| Q03 ما حكم الماء إذا سُخِّن بشيء نجس؟ | 1 | 1 | 4 | 1 | ✗ |
| Q04 ما درجة حديث «لا تفعلي فإنه يورث البرص» في الماء المسخن بالشمس؟ | 1 | 1 | 1 | 1 | ✗ |
| Q05 هل ينجس الماء الجاري القليل بمجرد ملاقاة النجاسة إذا لم يتغير؟ | 1 | 1 | 1 | 1 | ✗ |
| Q06 هل يكره الماء المسخن بطاهر كالحطب؟ | 1 | 1 | 1 | 1 | ✗ |
| Q08 لماذا قال البهوتي إن ماء زمزم لا يجوز الوضوء به؟ | 1 | 1 | 7 | 1 | ✗ |
| U1 ما هو أول باب في الفقه؟ | ✗ | 1 | 1 | 1 | ✗ |
| U2 كم أنواع المياه؟ | 3 | 3 | 1 | 1 | ✗ |
| U3 ما معنى الطهارة لغةً؟ | 2 | 1 | 1 | 1 | ✗ |
| U4 ما الفرق بين الطاهر والطهور؟ | 4 | 4 | 1 | 1 | ✗ |
| **Found in top 8** | **10/11** | **11/11** | **11/11** | **11/11** | **0/11** |

Notes:
- "Found in top 8" is lenient: it only needs one passage on a correct page. For U4 the old search found only the definition of طهور (rank 4), not of طاهر; the hybrid's top 8 holds both and Ibn Uthaymin's two-kinds view.
- U1 is answered from the anchor's table of contents, added as a citable passage (`toc_passages`).
- turath_find is shown for reference only: it needs every word to match and is designed for an AI model that refines its terms over several calls. One call with fixed key terms is not a fair test of it.
