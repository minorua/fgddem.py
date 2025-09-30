// FGD DEM Web Converter core logic (GML/XML to raster array)
document.getElementById('convertBtn').onclick = async function() {
  const fileInput = document.getElementById('fileInput');
  const output = document.getElementById('output');
  if (!fileInput.files.length) {
    output.textContent = 'ファイルを選択してください。';
    return;
  }
  const file = fileInput.files[0];
  if (file.name.endsWith('.xml')) {
    const text = await file.text();
    const result = parseJPGISGML(text);
    output.textContent = 'GMLパース結果: ' + JSON.stringify(result, null, 2);
  } else if (file.name.endsWith('.zip')) {
    output.textContent = 'ZIP対応は今後実装予定です。';
  } else {
    output.textContent = '対応していないファイル形式です。';
  }
};

function parseJPGISGML(text) {
  // GMLのheader/body/footer分割
  const [header, bodyWithFooter] = text.split('<gml:tupleList>');
  const [body, footer] = bodyWithFooter.split('</gml:tupleList>');
  const parser = new DOMParser();
  const doc = parser.parseFromString(header + footer, 'application/xml');
  // 範囲情報
  const lowerCorner = doc.querySelector('gml\\:lowerCorner').textContent.split(' ');
  const upperCorner = doc.querySelector('gml\\:upperCorner').textContent.split(' ');
  const lry = parseFloat(lowerCorner[0]);
  const ulx = parseFloat(lowerCorner[1]);
  const uly = parseFloat(upperCorner[0]);
  const lrx = parseFloat(upperCorner[1]);
  // サイズ
  const high = doc.querySelector('gml\\:high').textContent.split(' ');
  const xsize = parseInt(high[0]) + 1;
  const ysize = parseInt(high[1]) + 1;
  // 開始点
  const startPoint = doc.querySelector('gml\\:startPoint').textContent.split(' ');
  const startX = parseInt(startPoint[0]);
  const startY = parseInt(startPoint[1]);
  // ラスタ配列生成
  const narray = Array.from({length: ysize}, () => Array(xsize).fill(-9999));
  const tuples = body.trim().split(/\r?\n/);
  let i = 0, sx = startX;
  for (let y = startY; y < ysize; y++) {
    for (let x = sx; x < xsize; x++) {
      if (i < tuples.length) {
        const vals = tuples[i].split(',');
        if (vals.length === 2 && !vals[1].includes('-99')) {
          narray[y][x] = parseFloat(vals[1]);
        }
        i++;
      } else {
        break;
      }
    }
    if (i === tuples.length) break;
    sx = 0;
  }
  return {
    bounds: {lry, ulx, uly, lrx},
    size: {xsize, ysize},
    start: {startX, startY},
    raster: narray
  };
}
