"""Run with ComfyUI's Python to exercise real image tensors and random outputs."""
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class RandomNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec('torch') is None:
            raise unittest.SkipTest('Run these tensor tests with the ComfyUI Python interpreter')
        from aiohttp import web
        spec=importlib.util.spec_from_file_location('hairstyle_random_tests',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
        server=types.ModuleType('server');server.PromptServer=types.SimpleNamespace(instance=types.SimpleNamespace(routes=web.RouteTableDef()))
        previous_server=sys.modules.get('server');sys.modules['server']=server
        try:spec.loader.exec_module(module)
        finally:
            if previous_server is None:sys.modules.pop('server',None)
            else:sys.modules['server']=previous_server
        cls.module=module;cls.catalog=sys.modules[spec.name+'.catalog'];cls.node=module.RandomHairstyleGallery
    def setUp(self):
        from PIL import Image
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.old,self.old_user=self.catalog.LIBRARY,self.catalog.USER_LIBRARY
        self.catalog.LIBRARY,self.catalog.USER_LIBRARY=self.root/'builtin',self.root/'user'
        self.builtin={'id':'h-original','section':'hairstyle','section_zh':'假人发型','name_zh':'短发发型','title':'短发发型','name_ja':'','style':'','style_zh':'','hair':'ショート','hair_zh':'短发','source_id':'original','w':8,'h':12,'bytes':0,'full':'img/full/h-original.png','preview':'img/preview/h-original.webp','thumb':'img/thumb/h-original.webp'}
        index=self.catalog.LIBRARY/'data/hairstyle-zh.json';index.parent.mkdir(parents=True);index.write_text(json.dumps([self.builtin]))
        full=self.catalog.LIBRARY/self.builtin['full'];full.parent.mkdir(parents=True);Image.new('RGB',(8,12),'red').save(full)
        out=BytesIO();Image.new('RGB',(10,14),'blue').save(out,format='PNG')
        self.custom=self.module.import_image(out.getvalue(),name='自定义蓝发',other_name='My blue hair',filename='hair.png',root=self.catalog.USER_LIBRARY)
    def tearDown(self):
        self.catalog.LIBRARY,self.catalog.USER_LIBRARY=self.old,self.old_user;self.catalog._read_library.cache_clear();self.temp.cleanup()
    def test_sources_skip_missing_originals_and_support_custom_only_library(self):
        self.assertEqual({r['id'] for r in self.node._candidates()},{self.builtin['id'],self.custom['id']})
        self.assertEqual(self.node._candidates('builtin')[0]['id'],self.builtin['id'])
        self.assertEqual(self.node._candidates('user')[0]['id'],self.custom['id'])
        (self.catalog.LIBRARY/self.builtin['full']).unlink()
        self.assertEqual([r['id'] for r in self.node._candidates()],[self.custom['id']])
        (self.catalog.LIBRARY/'data/hairstyle-zh.json').unlink()
        self.assertIs(self.node.VALIDATE_INPUTS(),True)
    def test_empty_or_invalid_sources_produce_readable_validation_errors(self):
        self.assertIn('无效',self.node.VALIDATE_INPUTS('invalid'))
        (self.catalog.USER_LIBRARY/self.custom['full']).unlink()
        self.assertIn('没有可用',self.node.VALIDATE_INPUTS('user'))
        self.assertIn('No available',self.node.VALIDATE_INPUTS('user','en'))
        with self.assertRaises(ValueError):self.node().load_random('user')
    def test_each_call_resamples_and_all_eight_outputs_match_one_actual_reference(self):
        choices=[self.custom,self.builtin,self.custom]
        with patch.object(self.module.random,'choice',side_effect=choices) as choose:
            results=[self.node().load_random(language='en') for _ in range(3)]
        self.assertEqual(choose.call_count,3)
        for item,chosen in zip(results,choices):
            result=item['result'];self.assertEqual(len(result),8);self.assertEqual(result[3],chosen['id'])
            self.assertEqual(result[0].shape,(1,chosen['h'],chosen['w'],3));self.assertEqual(result[1:3],(chosen['w'],chosen['h']))
            row=self.catalog.hairstyle(chosen['id']);self.assertEqual(result[4],row['name_en']);self.assertEqual(result[6],row['hair_en']);self.assertEqual(result[7],row['source_id'])
            self.assertEqual(item['ui']['hairstyle_id'],[chosen['id']]);self.assertEqual(item['ui']['name'],[result[4]])
            rgb=result[0][0,0,0].tolist();self.assertEqual(rgb,[0.0,0.0,1.0] if chosen is self.custom else [1.0,0.0,0.0])
    def test_fresh_fingerprint_is_json_safe_and_original_node_stays_fixed(self):
        values=[self.node.IS_CHANGED() for _ in range(4)];self.assertEqual(len(set(values)),4);json.dumps(values,allow_nan=False)
        old=self.module.HairstyleGallery
        self.assertEqual(set(old.INPUT_TYPES()['required']),{'hairstyle_id'});self.assertEqual(set(old.INPUT_TYPES()['optional']),{'language'})
        self.assertEqual(old.IS_CHANGED(self.builtin['id']),old.IS_CHANGED(self.builtin['id']))
        first=old().load_hairstyle(self.builtin['id']);second=old().load_hairstyle(self.builtin['id'])
        self.assertIsInstance(first,tuple);self.assertEqual(first[3:],second[3:]);self.assertTrue(first[0].equal(second[0]));self.assertEqual(self.node.RETURN_NAMES,old.RETURN_NAMES)

if __name__=='__main__':unittest.main()
